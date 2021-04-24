from dataclasses import asdict, dataclass
from typing import Any, Iterator

from sqlalchemy import event, inspect
from sqlalchemy.engine import CursorResult
from sqlalchemy.future import Connection, Engine
from sqlalchemy.orm import (
    sessionmaker,
    InstanceState,
    ColumnProperty,
    Session,
    UOWTransaction,
    attributes,
)
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.sql import Select

from resql.database.models_audit import ChangeLog
from resql.database.models_recovery import QueryLog


@dataclass
class QueryLogger:
    session_maker: sessionmaker

    def __init__(self, target_engine: Engine) -> None:
        self.session_maker = sessionmaker(target_engine, future=True)

    def listen(self, engine: Engine) -> None:
        event.listen(engine, "after_execute", self.after_execute)

    def after_execute(
        self,
        conn: Connection,
        clauseelement: Any,
        multiparams: list[dict[str, Any]],
        params: dict[str, Any],
        execution_options: dict[str, Any],
        result: CursorResult,
    ) -> None:
        if isinstance(clauseelement, Select):
            return
        with self.session_maker.begin() as session:
            log = QueryLog(
                dialect_description=conn.dialect.dialect_description,
                statement=str(result.context.compiled),
                parameters=result.context.compiled_parameters,
                type=type(clauseelement).__name__,
            )
            session.add(log)


def log_queries(*, of: Engine, to: Engine) -> None:
    QueryLogger(to).listen(of)


@dataclass
class Diff:
    new: Any
    old: Any


@dataclass
class ModelHistory:
    diff: dict[str, dict[str, Any]]
    new_values: dict[str, Any]
    old_values: dict[str, Any]


def get_properties(state: InstanceState) -> Iterator[ColumnProperty]:
    for obj_col in state.mapper.local_table.c:
        # get the value of the attribute based on the MapperProperty related
        # to the mapped column.  this will allow usage of MapperProperties
        # that have a different keyname than that of the mapped column.
        try:
            yield state.mapper.get_property_by_column(obj_col)
        except UnmappedColumnError:
            # in the case of single table inheritance, there may be
            # columns on the mapped table intended for the subclass only.
            # the "unmapped" status of the subclass column on the
            # base class is a feature of the declarative module.
            continue


def obj_as_dict(obj: Any) -> dict[str, Any]:
    values = dict()
    properties = get_properties(inspect(obj))
    # cannot just use __dict__ because that also brings stuff other than the model attributes
    for prop in properties:
        # expired object attributes and also deferred cols might not be in the dict.
        # force it to load no matter what by using getattr().
        values[prop.key] = getattr(obj, prop.key)
    return values


def get_model_history(obj: Any) -> ModelHistory:
    state: InstanceState = inspect(obj)
    properties = get_properties(state)
    model_history = ModelHistory(old_values={}, new_values={}, diff={})
    for prop in properties:
        # expired object attributes and also deferred cols might not be in the dict.
        # force it to load no matter what by using getattr().
        if prop.key not in state.dict:
            getattr(obj, prop.key)

        history = attributes.get_history(obj, prop.key)
        if history.added and history.deleted:
            diff = Diff(old=history.deleted[0], new=history.added[0])
            model_history.diff[prop.key] = asdict(diff)
            model_history.old_values[prop.key] = diff.old
            model_history.new_values[prop.key] = diff.new
        elif history.added:
            diff = Diff(old=None, new=history.added[0])
            model_history.diff[prop.key] = asdict(diff)
            model_history.old_values[prop.key] = diff.old
            model_history.new_values[prop.key] = diff.new
        elif history.deleted:
            diff = Diff(old=history.deleted[0], new=None)
            model_history.diff[prop.key] = asdict(diff)
            model_history.old_values[prop.key] = diff.old
            model_history.new_values[prop.key] = diff.new
        elif history.unchanged:
            model_history.old_values[prop.key] = history.unchanged[0]
            model_history.new_values[prop.key] = history.unchanged[0]
    return model_history


@dataclass()
class ChangeLogger:
    session_maker: sessionmaker

    def __init__(self, target_engine: Engine) -> None:
        self.session_maker = sessionmaker(target_engine, future=True)

    def _log_delete(self, obj: Any) -> ChangeLog:
        return ChangeLog(
            table_name=getattr(obj, "__tablename__"),
            new_values=None,
            old_values=obj_as_dict(obj),
            diff=None,
            type="delete",
        )

    def _log_insert(self, obj: Any) -> ChangeLog:
        return ChangeLog(
            table_name=getattr(obj, "__tablename__"),
            new_values=obj_as_dict(obj),
            old_values=None,
            diff=None,
            type="insert",
        )

    def _log_update(self, obj: Any) -> ChangeLog:
        history = get_model_history(obj)
        return ChangeLog(
            table_name=getattr(obj, "__tablename__"),
            new_values=history.new_values,
            old_values=history.old_values,
            diff=history.diff,
            type="update",
        )

    def listen(self, session_maker: sessionmaker) -> None:
        event.listen(session_maker, "after_flush", self.after_flush)

    def after_flush(self, session: Session, _: UOWTransaction) -> None:
        with self.session_maker.begin() as target_session:
            for obj in session.deleted:
                target_session.add(self._log_delete(obj))
            for obj in session.dirty:
                target_session.add(self._log_update(obj))
            for obj in session.new:
                target_session.add(self._log_insert(obj))


def log_changes(*, of: sessionmaker, to: Engine) -> None:
    ChangeLogger(to).listen(of)
