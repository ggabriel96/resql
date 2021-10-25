from freezegun import freeze_time
from sqlalchemy import delete, select
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session, sessionmaker

from resql.auditing import log_changes
from resql.change_log import ChangeLog, OpType
from tests.models import Person
from tests.utils import now_in_utc


def test_orm_delete_should_be_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    # Arrange
    now = now_in_utc()
    person = Person(name="Someone", age=25)
    with production_mksession.begin() as session:
        session.add(person)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with freeze_time(now):
        with production_mksession.begin() as session:
            inserted_people = session.execute(select(Person).where(Person.name == "Someone")).scalars().all()
            assert len(inserted_people) == 1
            session.delete(inserted_people[0])

    # Assert the object was really deleted
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person)).scalars().all()
        assert inserted_people == []

    # Assert we audited the delete
    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == OpType.DELETE
        assert change_logs[0].executed_at == now
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[0].diff == {}
        assert change_logs[0].extra is None
        assert change_logs[0].record_id == person.id


def test_orm_enabled_delete_statement_is_not_audited(
    audit_engine: Engine,
    audit_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
    production_mksession: sessionmaker[Session],  # pylint: disable=unsubscriptable-object
) -> None:
    """
    See the warning in https://docs.sqlalchemy.org/en/14/orm/session_basics.html#selecting-a-synchronization-strategy:

    In order to intercept ORM-enabled UPDATE and DELETE operations with event handlers,
    use the SessionEvents.do_orm_execute() event.
    """
    # Arrange
    people = [
        Person(name="Person 1", age=1),
        Person(name="Person 2", age=2),
        Person(name="Person 3", age=3),
    ]
    with production_mksession.begin() as session:
        session.add_all(people)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:
        delete_result = session.execute(delete(Person).where(Person.age < 5))
        assert getattr(delete_result, "rowcount") == 3

    # Assert
    with production_mksession.begin() as session:
        inserted_people = session.execute(select(Person).order_by(Person.age)).scalars().all()
        assert inserted_people == []

    with audit_mksession.begin() as audit_session:
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert change_logs == []
