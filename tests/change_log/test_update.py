from freezegun import freeze_time
from sqlalchemy import select, update
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import Diff, log_changes
from resql.change_log import ChangeLog, OpType
from tests.models import Number, Person
from tests.utils import now_in_utc


def test_orm_update_should_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker,  # type: ignore[type-arg]
    production_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    now = now_in_utc()
    person = Person(name="Someone", age=25)
    expected_diff = dict(
        name=Diff(old="Someone", new="Someone Else"),
        age=Diff(old=25, new=50),
    )
    with production_mksession.begin() as session:
        session.add(person)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            inserted_people = session.execute(select(Person).where(Person.name == "Someone")).scalars().all()
            assert len(inserted_people) == 1
            assert inserted_people[0].name == expected_diff["name"]["old"]
            assert inserted_people[0].age == expected_diff["age"]["old"]
            inserted_people[0].name = "Someone Else"
            inserted_people[0].age = 50

    # Assert we didn't change the updated object
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == expected_diff["name"]["new"]
        assert inserted_people[0].age == expected_diff["age"]["new"]

    # Assert we audited the update
    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.UPDATE
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == person.id


def test_orm_enabled_update_statement_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker,  # type: ignore[type-arg]
    production_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    """
    See the warning in https://docs.sqlalchemy.org/en/14/orm/session_basics.html#selecting-a-synchronization-strategy:

    In order to intercept ORM-enabled UPDATE and DELETE operations with event handlers,
    use the SessionEvents.do_orm_execute() event.
    """
    # Arrange
    people = [
        Person(name="Update This 1", age=1),
        Person(name="This Is Correct", age=2),
        Person(name="Update This 2", age=3),
    ]
    with production_mksession.begin() as session:
        session.add_all(people)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:
        update_result = session.execute(
            update(Person)
            .where(Person.name.contains("Update This"))
            .values(name="This Is Correct")
            .execution_options(synchronize_session="fetch")
        )
        assert getattr(update_result, "rowcount") == 2

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.age)).scalars().all()
        assert len(inserted_people) == 3
        assert inserted_people[0].name == "This Is Correct"
        assert inserted_people[1].name == "This Is Correct"
        assert inserted_people[2].name == "This Is Correct"
        assert inserted_people[0].age == 1
        assert inserted_people[1].age == 2
        assert inserted_people[2].age == 3

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 0


def test_computed_columns_are_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker,  # type: ignore[type-arg]
    production_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    number_value_old = 3
    number_value_new = 5
    now = now_in_utc()
    expected_diff = dict(value=Diff(old=number_value_old, new=number_value_new))
    with production_mksession.begin() as session:
        number = Number(value=number_value_old)
        session.add(number)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            numbers_db = session.execute(select(Number)).scalars().all()
            assert len(numbers_db) == 1
            numbers_db[0].value = number_value_new

    # Assert we didn't change the updated object
    with production_mksession.begin() as session:
        numbers_db = session.execute(select(Number)).scalars().all()
        assert len(numbers_db) == 1
        assert numbers_db[0].id == number.id
        assert numbers_db[0].value == number_value_new
        assert numbers_db[0].doubled == number_value_new * 2

    # Assert we audited the insert
    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.UPDATE
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == Number.__tablename__
        assert change_logs[0].diff == expected_diff
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == number.id
