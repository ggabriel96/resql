from typing import Iterator

from fastapi import Header
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from examples.fastapi.database.models import Base as ProductionBase
from examples.fastapi.settings import Environment
from resql import change_log, query_log
from resql.auditing import log_changes, log_queries

AUDIT_ENGINE: Engine
PRODUCTION_ENGINE: Engine
RECOVERY_ENGINE: Engine
SESSION_MAKER: sessionmaker


def init_from_env(env: Environment) -> None:
    global AUDIT_ENGINE, PRODUCTION_ENGINE, RECOVERY_ENGINE, SESSION_MAKER  # pylint: disable=global-statement

    AUDIT_ENGINE = create_engine(env.audit_url, echo=True, future=True, logging_name="AUDITING")
    audit_registry = change_log.map_default()
    audit_registry.metadata.create_all(AUDIT_ENGINE)

    RECOVERY_ENGINE = create_engine(env.recovery_url, echo=True, future=True, logging_name="RECOVERY")
    recovery_registry = query_log.map_default()
    recovery_registry.metadata.create_all(RECOVERY_ENGINE)

    PRODUCTION_ENGINE = create_engine(env.production_url, echo=True, future=True, logging_name="PRODUCTN")
    ProductionBase.metadata.create_all(PRODUCTION_ENGINE)
    SESSION_MAKER = sessionmaker(PRODUCTION_ENGINE, future=True)
    log_queries(of=PRODUCTION_ENGINE, to=RECOVERY_ENGINE)


def begin_session(user_agent: str = Header(...)) -> Iterator[Session]:
    global AUDIT_ENGINE, SESSION_MAKER  # pylint: disable=global-statement
    with SESSION_MAKER.begin() as session:  # type: ignore # pylint: disable=no-member
        log_changes(of=session, to=AUDIT_ENGINE, extra=dict(user_agent=user_agent))
        yield session
