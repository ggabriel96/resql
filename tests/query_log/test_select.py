from sqlalchemy import select
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.auditing import log_queries
from resql.query_log import QueryLog
from tests.models import Person


def test_select_should_not_be_audited(
    recovery_engine: Engine,
    production_engine: Engine,
    recovery_mksession: sessionmaker,  # type: ignore[type-arg]
) -> None:
    # Arrange
    # Act
    with production_engine.connect() as conn:
        log_queries(of=conn, to=recovery_engine)
        inserted_people = conn.execute(select(Person)).all()
        assert inserted_people == []

    # Assert
    with recovery_mksession.begin() as audit_session:
        query_logs = audit_session.execute(select(QueryLog)).scalars().all()
        assert query_logs == []
