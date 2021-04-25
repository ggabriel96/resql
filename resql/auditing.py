from dataclasses import dataclass
from typing import Any, Iterator, Literal, TypedDict

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

from resql.models import ChangeLog, QueryLog


class QueryLogger:
    session_maker: sessionmaker

    def __init__(self, target_engine: Engine) -> None:
        self.session_maker = sessionmaker(target_engine, future=True)

    def listen(self, engine: Engine) -> None:
        event.listen(engine, "after_execute", self.after_execute)

    def after_execute(  # pylint: disable=too-many-arguments,unused-argument
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
        with self.session_maker.begin() as session:  # type: ignore[no-untyped-call] # pylint: disable=no-member
            log = QueryLog(
                dialect_description=conn.dialect.dialect_description,
                statement=str(result.context.compiled),
                parameters=result.context.compiled_parameters,
                type=type(clauseelement).__name__,
            )
            session.add(log)


def log_queries(*, of: Engine, to: Engine) -> QueryLogger:
    query_logger = QueryLogger(to)
    query_logger.listen(of)
    return query_logger


class Diff(TypedDict):
    # just to have predefined keys
    new: Any
    old: Any


@dataclass
class ModelDiff:
    values: dict[str, Diff]


def get_properties(state: InstanceState) -> Iterator[ColumnProperty]:
    for obj_col in state.mapper.local_table.c:  # type: ignore[attr-defined]
        # get the value of the attribute based on the MapperProperty related
        # to the mapped column.  this will allow usage of MapperProperties
        # that have a different keyname than that of the mapped column.
        try:
            yield state.mapper.get_property_by_column(obj_col)  # type: ignore[attr-defined]
        except UnmappedColumnError:
            # in the case of single table inheritance, there may be
            # columns on the mapped table intended for the subclass only.
            # the "unmapped" status of the subclass column on the
            # base class is a feature of the declarative module.
            continue


def get_model_diff(obj: Any) -> ModelDiff:
    state: InstanceState = inspect(obj)
    properties = get_properties(state)
    model_diff = ModelDiff(values={})
    for prop in properties:
        # expired object attributes and also deferred cols might not be in the dict.
        # force it to load no matter what by using getattr().
        if prop.key not in state.dict:
            getattr(obj, prop.key)

        history = attributes.get_history(obj, prop.key)
        if history.added and history.deleted:
            model_diff.values[prop.key] = Diff(old=history.deleted[0], new=history.added[0])
        elif history.added:
            model_diff.values[prop.key] = Diff(old=None, new=history.added[0])
        elif history.deleted:
            model_diff.values[prop.key] = Diff(old=history.deleted[0], new=None)
    return model_diff


class ChangeLogger:
    session_maker: sessionmaker

    def __init__(self, target_engine: Engine) -> None:
        self.session_maker = sessionmaker(target_engine, future=True)

    @staticmethod
    def _new_log(obj: Any, log_type: Literal["delete", "insert", "update"]) -> ChangeLog:
        diff = get_model_diff(obj)
        return ChangeLog(
            table_name=getattr(obj, "__tablename__"),
            diff=diff.values,
            type=log_type,
        )

    def listen(self, session_maker: sessionmaker) -> None:
        event.listen(session_maker, "after_flush", self.after_flush)

    def after_flush(self, session: Session, _: UOWTransaction) -> None:
        with self.session_maker.begin() as target_session:  # type: ignore[no-untyped-call] # pylint: disable=no-member
            for obj in session.deleted:
                target_session.add(self._new_log(obj, "delete"))
            for obj in session.dirty:
                target_session.add(self._new_log(obj, "update"))
            for obj in session.new:
                target_session.add(self._new_log(obj, "insert"))


def log_changes(*, of: sessionmaker, to: Engine) -> ChangeLogger:
    change_logger = ChangeLogger(to)
    change_logger.listen(of)
    return change_logger
