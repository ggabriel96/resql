import copy
from typing import Any

import pytest
from freezegun import freeze_time
from sqlalchemy import insert, select, text
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session, sessionmaker

from resql.auditing import Diff, log_changes
from resql.change_log import ChangeLog, OpType
from tests.models import ImperativeModel, ImperativeTable, Number, Person
from tests.utils import now_in_utc


def assert_inserted_people_data(inserted_people: list[Person], expected_people: list[dict[str, Any]]) -> None:
    assert len(inserted_people) == len(expected_people)
    for inserted, expected in zip(inserted_people, expected_people):
        assert inserted.name == expected["name"]
        assert inserted.age == expected["age"]


def test_orm_insert_should_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    now = now_in_utc()
    person_data = dict(name="Someone", age=25)
    expected_diff = dict(
        name=Diff(old=None, new="Someone"),
        age=Diff(old=None, new=25),
    )

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            person = Person(**person_data)  # type: ignore[arg-type]
            session.add(person)

    # Assert we didn't change the inserted object
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert_inserted_people_data(inserted_people, [person_data])

    # Assert we audited the insert
    with audit_mksession.begin() as audit_session:
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.diff["name"]["new"].as_string())).scalars().all()
        )
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == person.id


def test_many_orm_inserts_should_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    now = now_in_utc()
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
    with freeze_time(now):
        with production_mksession.begin() as session:
            people = [Person(**data) for data in people_data]  # type: ignore[arg-type]
            session.add_all(people)

    # Assert we didn't change the inserted objects
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert_inserted_people_data(inserted_people, people_data)

    # Assert we audited the inserts
    with audit_mksession.begin() as audit_session:
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.diff["name"]["new"].as_string())).scalars().all()
        )
        assert len(change_logs) == 3
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[1].type == OpType.INSERT
        assert change_logs[2].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[1].executed_at == now
        assert change_logs[2].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[2].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[2].diff == expected_diffs[2]
        assert change_logs[0].extra is None
        assert change_logs[1].extra is None
        assert change_logs[2].extra is None
        assert change_logs[0].record_id == people[0].id
        assert change_logs[1].record_id == people[1].id
        assert change_logs[2].record_id == people[2].id


def test_rolled_back_orm_insert_should_not_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    person = Person(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession() as session:
        session.add(person)
        session.rollback()

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).all()
        assert len(inserted_people) == 0

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_orm_insert_rolled_back_by_exception_should_not_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    person = Person(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with pytest.raises(RuntimeError):
        with production_mksession.begin() as session:
            session.add(person)
            raise RuntimeError("nope")

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).all()
        assert len(inserted_people) == 0

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_computed_columns_are_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    number_value = 3
    now = now_in_utc()
    expected_diff = dict(value=Diff(old=None, new=number_value))

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            number = Number(value=number_value)
            session.add(number)

    # Assert we didn't change the inserted object
    with production_mksession.begin() as session:
        numbers_db = session.execute(select(Number)).scalars().all()
        assert len(numbers_db) == 1
        assert numbers_db[0].id == number.id
        assert numbers_db[0].value == number_value
        assert numbers_db[0].doubled == number_value * 2

    # Assert we audited the insert
    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == Number.__tablename__
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == number.id


def test_core_insert_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    person = dict(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:
        session.execute(insert(Person).values(**person))

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert_inserted_people_data(inserted_people, [person])

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_many_core_inserts_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    people = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]

    # Act
    log_changes(of=production_mksession, to=audit_engine)

    with production_mksession.begin() as session:
        session.execute(insert(Person), people)

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert_inserted_people_data(inserted_people, people)

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_text_insert_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    person = dict(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:
        session.execute(text("INSERT INTO person(name, age) VALUES (:name, :age)").bindparams(**person))

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert_inserted_people_data(inserted_people, [person])

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_many_text_inserts_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    people = [dict(name="A", age=1), dict(name="B", age=2), dict(name="C", age=3)]

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:
        session.execute(text("INSERT INTO person(name, age) VALUES (:name, :age)"), people)

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert_inserted_people_data(inserted_people, people)

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []


def test_extra_field_is_reused_across_commits(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    # pylint: disable=too-many-locals
    now = now_in_utc()
    extra = dict(user_agent="testing")
    person_1_data = dict(name="A", age=1)
    person_2_data = dict(name="B", age=2)
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
        with freeze_time(now):
            person_1 = Person(**person_1_data)  # type: ignore[arg-type]
            session.add(person_1)
            session.commit()

            person_2 = Person(**person_2_data)  # type: ignore[arg-type]
            session.add(person_2)
            session.commit()

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert len(inserted_people) == 2
        assert inserted_people[0].name == person_1_data["name"]
        assert inserted_people[0].age == person_1_data["age"]
        assert inserted_people[1].name == person_2_data["name"]
        assert inserted_people[1].age == person_2_data["age"]

    with audit_mksession.begin() as audit_session:
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.diff["name"]["new"].as_string())).scalars().all()
        )
        assert len(change_logs) == 2
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[1].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[1].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[0].extra == extra
        assert change_logs[1].extra == extra
        assert change_logs[0].record_id == person_1.id
        assert change_logs[1].record_id == person_2.id


def test_extra_field_is_saved_independently_for_concurrent_sessions(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # pylint: disable=too-many-locals
    # Arrange
    now = now_in_utc()
    extra_1 = dict(session_no=1)
    extra_2 = dict(session_no=2)
    people_data = [dict(name="A", age=1), dict(name="B", age=2)]
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
    with freeze_time(now):  # not sure why this had to be the outermost context manager to work
        with production_mksession.begin() as session_1:
            with production_mksession.begin() as session_2:
                log_changes(of=session_1, to=audit_engine, extra=copy.deepcopy(extra_1))
                log_changes(of=session_2, to=audit_engine, extra=copy.deepcopy(extra_2))
                person_1 = Person(**people_data[0])  # type: ignore[arg-type]
                session_1.add(person_1)
                person_2 = Person(**people_data[1])  # type: ignore[arg-type]
                session_2.add(person_2)

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.name)).scalars().all()
        assert_inserted_people_data(inserted_people, people_data)

    with audit_mksession.begin() as audit_session:
        change_logs = (
            audit_session.execute(select(ChangeLog).order_by(ChangeLog.diff["name"]["new"].as_string())).scalars().all()
        )
        assert len(change_logs) == 2
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[1].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[1].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[1].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diffs[0]
        assert change_logs[1].diff == expected_diffs[1]
        assert change_logs[0].extra == extra_1
        assert change_logs[1].extra == extra_2
        assert change_logs[0].record_id == person_1.id
        assert change_logs[1].record_id == person_2.id


def test_table_mapped_imperatively_should_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    now = now_in_utc()
    imperative_data = dict(value="imperative")
    expected_diff = dict(
        value=Diff(old=None, new="imperative"),
    )

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            imperative = ImperativeModel(**imperative_data)  # type: ignore[call-arg]
            session.add(imperative)

    # Assert we didn't change the inserted object
    with production_mksession.begin() as session:
        inserted_imperatives = session.execute(select(ImperativeModel)).scalars().all()
        assert len(inserted_imperatives) == 1
        assert inserted_imperatives[0].value == imperative_data["value"]

    # Assert we audited the insert
    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.INSERT
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == ImperativeTable.name
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == imperative.id
