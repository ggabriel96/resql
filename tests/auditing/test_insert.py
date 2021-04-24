import datetime as dt

from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.database.auditing import Diff, log_changes
from resql.database.models_audit import ChangeLog
from tests.models import Person


def test_orm_insert_should_be_audited(
    audit_engine: Engine,
    production_engine: Engine,
    audit_mksession: sessionmaker,
    production_mksession: sessionmaker,
) -> None:
    # Arrange
    now = dt.datetime.utcnow()
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
            assert change_logs[0].executed_at <= now
            assert change_logs[0].table_name == Person.__tablename__
            assert change_logs[0].diff == expected_diff
