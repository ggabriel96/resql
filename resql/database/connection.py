from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from resql.database.auditing import ChangeLogger, QueryLogger
from resql.database.models import mapper_registry as experiment_registry
from resql.database.models_audit import mapper_registry as audit_registry
from resql.database.models_recovery import mapper_registry as recovery_registry


AUDIT_ENGINE = create_engine(
    "postgresql+psycopg2://postgres:1234@127.0.0.1:5432/audit",
    echo=True,
    future=True,
    logging_name="AUDIT",
)
EXPERIMENT_ENGINE = create_engine(
    "postgresql+psycopg2://postgres:1234@127.0.0.1:5432/experiment",
    echo=True,
    future=True,
    logging_name="EXPERIMENT",
)
RECOVERY_ENGINE = create_engine(
    "postgresql+psycopg2://postgres:1234@127.0.0.1:5432/recovery",
    echo=True,
    future=True,
    logging_name="RECOVERY",
)


audit_registry.metadata.create_all(AUDIT_ENGINE)
experiment_registry.metadata.create_all(EXPERIMENT_ENGINE)
recovery_registry.metadata.create_all(RECOVERY_ENGINE)

LOGGER = QueryLogger(session_maker=sessionmaker(RECOVERY_ENGINE, future=True))
event.listen(EXPERIMENT_ENGINE, "after_execute", LOGGER.after_execute)


@dataclass
class AuditedSession:
    session_maker = sessionmaker(EXPERIMENT_ENGINE, future=True)
    _rescue_session_maker = sessionmaker(AUDIT_ENGINE, future=True)

    @contextmanager
    def begin(self) -> Iterator[Session]:
        with ExitStack() as stack:
            rescue_session = stack.enter_context(self._rescue_session_maker.begin())
            session = stack.enter_context(self.session_maker.begin())
            ChangeLogger(target_session=rescue_session).listen(session)
            yield session


SESSION = AuditedSession()
