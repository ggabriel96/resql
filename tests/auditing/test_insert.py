import datetime as dt

from sqlalchemy import insert, select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import Diff, log_changes
from resql.models import ChangeLog
from tests.models import Person


def test_orm_insert_should_be_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    now = dt.datetime.utcnow().replace(microsecond=0)
    dt_before = now - dt.timedelta(seconds=1)
    dt_after = now + dt.timedelta(seconds=1)
    person = Person(name="Someone", age=25)
    expected_diff = dict(
        name=Diff(old=None, new="Someone"),
        age=Diff(old=None, new=25),
    )

    # Act
    log_changes(of=production_mksession, to=audit_engine)

    with production_mksession() as session:
        session.add(person)
        session.commit()

        # Assert
        with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
            change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
            assert len(change_logs) == 1
            assert change_logs[0].type == "insert"
            assert dt_before <= change_logs[0].executed_at <= dt_after
            assert change_logs[0].table_name == Person.__tablename__
            assert change_logs[0].diff == expected_diff


def test_core_insert_is_not_audited(
    audit_engine: Engine, audit_mksession: sessionmaker, production_mksession: sessionmaker
) -> None:
    # Arrange
    person = dict(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)

    with production_mksession() as session:
        session.execute(insert(Person).values(**person))
        session.commit()

        # Assert
        with audit_mksession.begin() as audit_session:  # type: ignore[no-untyped-call]
            change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
            assert change_logs == []
