from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.database.auditing import ChangeLog, log_changes
from tests.models import Person


def test_orm_insert_should_be_audited(
    audit_engine: Engine,
    production_engine: Engine,
    audit_mksession: sessionmaker,
    production_mksession: sessionmaker,
) -> None:
    # Arrange
    person = Person(name="Someone", age=25)

    # Act
    log_changes(of=production_mksession, to=audit_engine)

    with production_mksession() as session:
        session.add(person)
        session.commit()

        # Assert
        with audit_mksession.begin() as audit_session:
            change_logs = audit_session.execute(select(ChangeLog)).scalars().all()
            assert len(change_logs) == 1
