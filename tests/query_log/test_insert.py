import copy
from typing import Any

from freezegun import freeze_time
from sqlalchemy import insert, select
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session, sessionmaker

from resql.auditing import log_queries
from resql.change_log import OpType
from resql.query_log import QueryLog
from tests.models import Person
from tests.utils import now_in_utc


def assert_inserted_people_data(inserted_people: list[Person], expected_people: list[dict[str, Any]]) -> None:
    assert len(inserted_people) == len(expected_people)
    for inserted, expected in zip(inserted_people, expected_people):
        assert inserted.name == expected["name"]
        assert inserted.age == expected["age"]


def test_orm_insert_should_be_audited(
    recovery_engine: Engine,
    production_engine: Engine,
    production_mksession: sessionmaker,  # type: ignore[type-arg]
    recovery_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    now = now_in_utc()
    person_data = dict(name="Someone", age=25)

    # Act
    # use connection so we don't audit the Engine globally, leaking to other tests
    with production_engine.connect() as conn:
        log_queries(of=conn, to=recovery_engine)
        with freeze_time(now):
            with Session(conn, future=True) as session, session.begin():
                person = Person(**person_data)  # type: ignore[arg-type]
                session.add(person)

    # Assert we didn't change the inserted object
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert_inserted_people_data(inserted_people, [person_data])

    # Assert we audited the query
    with recovery_mksession.begin() as recovery_session:
        query_logs: list[QueryLog] = recovery_session.execute(select(QueryLog)).scalars().all()
        assert len(query_logs) == 1
        assert query_logs[0].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[0].executed_at == now
        assert query_logs[0].extra is None
        assert query_logs[0].parameters == [person_data]
        assert Person.__tablename__ in query_logs[0].statement
        assert query_logs[0].type == OpType.INSERT


def test_many_core_inserts_should_be_audited(
    recovery_engine: Engine,
    production_engine: Engine,
    production_mksession: sessionmaker,  # type: ignore[type-arg]
    recovery_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    now = now_in_utc()
    people = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]

    # Act
    # use connection so we don't audit the Engine globally, leaking to other tests
    with production_engine.connect() as conn:
        log_queries(of=conn, to=recovery_engine)
        with freeze_time(now):
            with Session(conn, future=True) as session, session.begin():
                session.execute(insert(Person), people)

    # Assert we didn't change the inserted objects
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert_inserted_people_data(inserted_people, people)

    # Assert we audited the query
    with recovery_mksession.begin() as recovery_session:
        query_logs: list[QueryLog] = recovery_session.execute(select(QueryLog)).scalars().all()
        assert len(query_logs) == 1
        assert query_logs[0].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[0].executed_at == now
        assert query_logs[0].extra is None
        assert query_logs[0].parameters == people
        assert Person.__tablename__ in query_logs[0].statement
        assert query_logs[0].type == OpType.INSERT


def test_extra_field_is_reused_across_commits_on_same_engine(
    recovery_engine: Engine,
    production_engine: Engine,
    recovery_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    now = now_in_utc()
    extra = dict(user_agent="testing")
    person_1 = dict(name="A", age=1)
    person_2 = dict(name="B", age=2)

    # Act
    with production_engine.connect() as conn:
        with freeze_time(now):
            log_queries(of=conn, to=recovery_engine, extra=copy.deepcopy(extra))
            conn.execute(insert(Person).values(**person_1))
            conn.commit()
            conn.execute(insert(Person).values(**person_2))
            conn.commit()

    # Assert
    with production_engine.connect() as conn:
        inserted_people = conn.execute(select(Person).order_by(Person.name)).all()
        assert len(inserted_people) == 2

    with recovery_mksession.begin() as audit_session:
        query_logs = audit_session.execute(select(QueryLog).order_by(QueryLog.id)).scalars().all()
        assert len(query_logs) == 2
        assert query_logs[0].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[1].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[0].executed_at == now
        assert query_logs[1].executed_at == now
        assert query_logs[0].extra == extra
        assert query_logs[1].extra == extra
        assert query_logs[0].type == OpType.INSERT
        assert query_logs[1].type == OpType.INSERT


def test_extra_field_is_saved_independently_for_concurrent_connections(
    recovery_engine: Engine,
    production_engine: Engine,
    recovery_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    now = now_in_utc()
    extra_1 = dict(session_no=1)
    extra_2 = dict(session_no=2)
    people = [dict(name="A", age=1), dict(name="B", age=2)]

    # Act
    with freeze_time(now):
        with production_engine.connect() as conn_1:
            log_queries(of=conn_1, to=recovery_engine, extra=copy.deepcopy(extra_1))
            with production_engine.connect() as conn_2:
                log_queries(of=conn_2, to=recovery_engine, extra=copy.deepcopy(extra_2))

                conn_1.execute(insert(Person).values(**people[0]))
                conn_1.commit()
                conn_2.execute(insert(Person).values(**people[1]))
                conn_2.commit()

    # Assert
    with production_engine.connect() as conn:
        inserted_people = conn.execute(select(Person).order_by(Person.name)).all()
        assert len(inserted_people) == 2

    with recovery_mksession.begin() as audit_session:
        query_logs = audit_session.execute(select(QueryLog).order_by(QueryLog.id)).scalars().all()
        assert len(query_logs) == 2
        assert query_logs[0].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[1].dialect_description == getattr(production_engine.dialect, "dialect_description", ...)
        assert query_logs[0].executed_at == now
        assert query_logs[1].executed_at == now
        assert query_logs[0].extra == extra_1
        assert query_logs[1].extra == extra_2
        assert query_logs[0].type == OpType.INSERT
        assert query_logs[1].type == OpType.INSERT
