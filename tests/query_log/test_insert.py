import copy
import datetime as dt

from sqlalchemy import insert, select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import log_queries
from resql.models import QueryLog
from tests.models import Person


def test_extra_field_is_reused_across_commits_on_same_engine(
    recovery_now: dt.datetime, recovery_engine: Engine, production_engine: Engine, recovery_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = recovery_now - dt.timedelta(seconds=1)
    dt_after = recovery_now + dt.timedelta(seconds=1)
    extra = dict(user_agent="testing")
    person_1 = dict(name="A", age=1)
    person_2 = dict(name="B", age=2)

    # Act
    with production_engine.connect() as conn:  # type: ignore[no-untyped-call]
        log_queries(of=conn, to=recovery_engine, extra=copy.deepcopy(extra))
        conn.execute(insert(Person).values(**person_1))
        conn.commit()
        conn.execute(insert(Person).values(**person_2))
        conn.commit()

    # Assert
    with production_engine.connect() as conn:  # type: ignore[no-untyped-call]
        inserted_people = conn.execute(select(Person).order_by(Person.name)).all()
        assert len(inserted_people) == 2

    with recovery_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        query_logs = audit_session.execute(select(QueryLog).order_by(QueryLog.id)).scalars().all()
        assert len(query_logs) == 2
        assert query_logs[0].dialect_description == production_engine.dialect.dialect_description
        assert query_logs[1].dialect_description == production_engine.dialect.dialect_description
        assert dt_before <= query_logs[0].executed_at <= dt_after
        assert dt_before <= query_logs[1].executed_at <= dt_after
        assert query_logs[0].extra == extra
        assert query_logs[1].extra == extra
        assert query_logs[0].type == "Insert"
        assert query_logs[1].type == "Insert"


def test_extra_field_is_saved_independently_for_concurrent_connections(
    recovery_now: dt.datetime, recovery_engine: Engine, production_engine: Engine, recovery_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = recovery_now - dt.timedelta(seconds=1)
    dt_after = recovery_now + dt.timedelta(seconds=1)
    extra_1 = dict(session_no=1)
    extra_2 = dict(session_no=2)
    people = [dict(name="A", age=1), dict(name="B", age=2)]

    # Act
    with production_engine.connect() as conn_1:  # type: ignore[no-untyped-call]
        log_queries(of=conn_1, to=recovery_engine, extra=copy.deepcopy(extra_1))
        with production_engine.connect() as conn_2:  # type: ignore[no-untyped-call]
            log_queries(of=conn_2, to=recovery_engine, extra=copy.deepcopy(extra_2))

            conn_1.execute(insert(Person).values(**people[0]))
            conn_1.commit()
            conn_2.execute(insert(Person).values(**people[1]))
            conn_2.commit()

    # Assert
    with production_engine.connect() as conn:  # type: ignore[no-untyped-call]
        inserted_people = conn.execute(select(Person).order_by(Person.name)).all()
        assert len(inserted_people) == 2

    with recovery_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        query_logs = audit_session.execute(select(QueryLog).order_by(QueryLog.id)).scalars().all()
        assert len(query_logs) == 2
        assert query_logs[0].dialect_description == production_engine.dialect.dialect_description
        assert query_logs[1].dialect_description == production_engine.dialect.dialect_description
        assert dt_before <= query_logs[0].executed_at <= dt_after
        assert dt_before <= query_logs[1].executed_at <= dt_after
        assert query_logs[0].extra == extra_1
        assert query_logs[1].extra == extra_2
        assert query_logs[0].type == "Insert"
        assert query_logs[1].type == "Insert"
