from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.future import Engine
from sqlalchemy.orm import Session, sessionmaker

from resql.auditing import log_changes, log_queries
from resql.models import AuditingBase, RecoveryBase

from examples.fastapi.settings import Environment
from examples.fastapi.database.models import Base as ProductionBase


class Engines:
    production: Optional[Engine] = None
    audit: Optional[Engine] = None
    recovery: Optional[Engine] = None


engines = Engines()
session_maker: Optional[sessionmaker] = None  # pylint: disable=invalid-name


def init_from_env(env: Environment) -> None:
    global engines, session_maker  # pylint: disable=global-statement, invalid-name

    engines.production = create_engine(  # type: ignore[assignment]
        env.production_url, echo=True, future=True, logging_name="PRODUCTN"
    )
    ProductionBase.metadata.create_all(engines.production)

    engines.audit = create_engine(  # type: ignore[assignment]
        env.audit_url, echo=True, future=True, logging_name="AUDITING"
    )
    AuditingBase.metadata.create_all(engines.audit)

    engines.recovery = create_engine(  # type: ignore[assignment]
        env.recovery_url, echo=True, future=True, logging_name="RECOVERY"
    )
    RecoveryBase.metadata.create_all(engines.recovery)

    session_maker = sessionmaker(engines.production, future=True)

    assert engines.production is not None
    assert engines.recovery is not None
    log_queries(of=engines.production, to=engines.recovery)


def begin_session() -> Iterator[Session]:
    global engines, session_maker  # pylint: disable=global-statement, invalid-name
    with session_maker.begin() as session:  # type: ignore # pylint: disable=no-member
        assert engines.audit is not None
        log_changes(of=session, to=engines.audit)
        yield session
