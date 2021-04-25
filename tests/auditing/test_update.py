import datetime as dt

from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import Diff, log_changes
from resql.models import ChangeLog
from tests.models import Person


def test_orm_update_should_be_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    now = dt.datetime.utcnow().replace(microsecond=0)
    dt_before = now - dt.timedelta(seconds=1)
    dt_after = now + dt.timedelta(seconds=1)
    person = Person(name="Someone", age=25)
    expected_diff = dict(
        name=Diff(old="Someone", new="Someone Else"),
        age=Diff(old=25, new=50),
    )
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        session.add(person)

    # Act
    log_changes(of=production_mksession, to=audit_engine)
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person).where(Person.name == "Someone")).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == expected_diff["name"]["old"]  # pylint: disable=unsubscriptable-object
        assert inserted_people[0].age == expected_diff["age"]["old"]  # pylint: disable=unsubscriptable-object
        inserted_people[0].name = "Someone Else"
        inserted_people[0].age = 50

    # Assert we didn't change the updated object
    with production_mksession.begin() as session:  # type: ignore[no-untyped-call]
        inserted_people = session.execute(select(Person)).scalars().all()
        assert len(inserted_people) == 1
        assert inserted_people[0].name == expected_diff["name"]["new"]  # pylint: disable=unsubscriptable-object
        assert inserted_people[0].age == expected_diff["age"]["new"]  # pylint: disable=unsubscriptable-object

    # Assert we audited the update
    with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
        change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
        assert len(change_logs) == 1
        assert change_logs[0].type == "update"
        assert dt_before <= change_logs[0].executed_at <= dt_after
        assert change_logs[0].table_name == Person.__tablename__
        assert change_logs[0].diff == expected_diff
