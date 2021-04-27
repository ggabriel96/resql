import copy
import datetime as dt

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import Diff, log_changes
from resql.models import ChangeLog
from tests.models import Person


def test_orm_insert_should_be_audited(
    audit_now: dt.datetime, audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = audit_now - dt.timedelta(seconds=1)
    dt_after = audit_now + dt.timedelta(seconds=1)
    person_data = dict(name="Someone", age=25)
    expected_diff = dict(
        name=Diff(old=None, new="Someone"),
        age=Diff(old=None, new=25),
    )

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        person = Person(**person_data)  # type: ignore[arg-type]
        session.add(person)

    # Assert we didn't change the inserted object
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == person_data["name"]
        assert inserted_people[0].age == person_data["age"]

    # Assert we audited the insert
    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == "insert"
        assert dt_before <= change_logs[0].executed_at <= dt_after
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None


def test_many_orm_inserts_should_be_audited(
    audit_now: dt.datetime, audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = audit_now - dt.timedelta(seconds=1)
    dt_after = audit_now + dt.timedelta(seconds=1)
    people_data = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]
    expected_diffs = [
        dict(
            name=Diff(old=None, new="A"),
            age=Diff(old=None, new=1),
        ),
        dict(
            name=Diff(old=None, new="B"),
            age=Diff(old=None, new=2),
        ),
        dict(
            name=Diff(old=None, new="C"),
            age=Diff(old=None, new=3),
        ),
    ]

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        people = [Person(**data) for data in people_data]  # type: ignore[arg-type]
        session.add_all(people)

    # Assert we didn't change the inserted objects
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert len(inserted_people) == 3
        assert inserted_people[0].name == people_data[0]["name"]
        assert inserted_people[0].age == people_data[0]["age"]
        assert inserted_people[1].name == people_data[1]["name"]
        assert inserted_people[1].age == people_data[1]["age"]
        assert inserted_people[2].name == people_data[2]["name"]
        assert inserted_people[2].age == people_data[2]["age"]

    # Assert we audited the inserts
    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 3
        assert change_logs[0].type == "insert"
        assert change_logs[1].type == "insert"
        assert change_logs[2].type == "insert"
        assert dt_before <= change_logs[0].executed_at <= dt_after
        assert dt_before <= change_logs[1].executed_at <= dt_after
        assert dt_before <= change_logs[2].executed_at <= dt_after
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[2].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[2].diff == expected_diffs[2]
        assert change_logs[0].extra is None
        assert change_logs[1].extra is None
        assert change_logs[2].extra is None


def test_rolled_back_orm_insert_should_not_be_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    person = Person(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession() as session:
        session.add(person)
        session.rollback()

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).all()
        assert len(inserted_people) == 0

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_orm_insert_rolled_back_by_exception_should_not_be_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    person = Person(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with pytest.raises(RuntimeError):
        with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
            session.add(person)
            raise RuntimeError("nope")

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).all()
        assert len(inserted_people) == 0

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_core_insert_is_not_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    person = dict(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        session.execute(insert(Person).values(**person))

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == person["name"]
        assert inserted_people[0].age == person["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_many_core_inserts_is_not_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    people = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]

    # Act
    log_changes(of=production_mksession, to=audit_engine)

    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        session.execute(insert(Person), people)

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 3
        assert inserted_people[0].name == people[0]["name"]
        assert inserted_people[0].age == people[0]["age"]
        assert inserted_people[1].name == people[1]["name"]
        assert inserted_people[1].age == people[1]["age"]
        assert inserted_people[2].name == people[2]["name"]
        assert inserted_people[2].age == people[2]["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_text_insert_is_not_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    person = dict(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        session.execute(text("INSERT INTO person(name, age) VALUES (:name, :age)").bindparams(**person))

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == person["name"]
        assert inserted_people[0].age == person["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_many_text_inserts_is_not_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    people = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        session.execute(text("INSERT INTO person(name, age) VALUES (:name, :age)"), people)

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 3
        assert inserted_people[0].name == people[0]["name"]
        assert inserted_people[0].age == people[0]["age"]
        assert inserted_people[1].name == people[1]["name"]
        assert inserted_people[1].age == people[1]["age"]
        assert inserted_people[2].name == people[2]["name"]
        assert inserted_people[2].age == people[2]["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_extra_field_is_reused_across_commits(
    audit_now: dt.datetime, audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = audit_now - dt.timedelta(seconds=1)
    dt_after = audit_now + dt.timedelta(seconds=1)
    extra = dict(user_agent="testing")
    person_1 = dict(name="A", age=1)
    person_2 = dict(name="B", age=2)
    expected_diffs = [
        dict(
            name=Diff(old=None, new="A"),
            age=Diff(old=None, new=1),
        ),
        dict(
            name=Diff(old=None, new="B"),
            age=Diff(old=None, new=2),
        ),
    ]

    # Act
    with production_mksession() as session:
        log_changes(of=session, to=audit_engine, extra=copy.deepcopy(extra))
        session.add(Person(**person_1))  # type: ignore[arg-type]
        session.commit()
        session.add(Person(**person_2))  # type: ignore[arg-type]
        session.commit()

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert len(inserted_people) == 2
        assert inserted_people[0].name == person_1["name"]
        assert inserted_people[0].age == person_1["age"]
        assert inserted_people[1].name == person_2["name"]
        assert inserted_people[1].age == person_2["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.diff["name"]["new"].as_string())).scalars().all()
        )
        assert len(change_logs) == 2
        assert change_logs[0].type == "insert"
        assert change_logs[1].type == "insert"
        assert dt_before <= change_logs[0].executed_at <= dt_after
        assert dt_before <= change_logs[1].executed_at <= dt_after
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[0].extra == extra
        assert change_logs[1].extra == extra


def test_extra_field_is_saved_independently_for_concurrent_sessions(
    audit_now: dt.datetime, audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    dt_before = audit_now - dt.timedelta(seconds=1)
    dt_after = audit_now + dt.timedelta(seconds=1)
    person_1 = dict(name="A", age=1)
    person_2 = dict(name="B", age=2)
    expected_diffs = [
        dict(
            name=Diff(old=None, new="A"),
            age=Diff(old=None, new=1),
        ),
        dict(
            name=Diff(old=None, new="B"),
            age=Diff(old=None, new=2),
        ),
    ]

    # Act
    with production_mksession.begin() as session_1:  # type: ignore[no-untyped-call]
        with production_mksession.begin() as session_2:  # type: ignore[no-untyped-call]
            log_changes(of=session_1, to=audit_engine, extra=dict(session_no=1))
            log_changes(of=session_2, to=audit_engine, extra=dict(session_no=2))
            session_1.add(Person(**person_1))  # type: ignore[arg-type]
            session_2.add(Person(**person_2))  # type: ignore[arg-type]

    # Assert
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert len(inserted_people) == 2
        assert inserted_people[0].name == person_1["name"]
        assert inserted_people[0].age == person_1["age"]
        assert inserted_people[1].name == person_2["name"]
        assert inserted_people[1].age == person_2["age"]

    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.extra["session_no"].as_string())).scalars().all()
        )
        assert len(change_logs) == 2
        assert change_logs[0].type == "insert"
        assert change_logs[1].type == "insert"
        assert dt_before <= change_logs[0].executed_at <= dt_after
        assert dt_before <= change_logs[1].executed_at <= dt_after
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[0].extra == dict(session_no=1)
        assert change_logs[1].extra == dict(session_no=2)
