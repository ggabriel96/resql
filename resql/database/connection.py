from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from resql.database.auditing import Auditor, QueryLogger
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
    _audit_session_maker = sessionmaker(AUDIT_ENGINE, future=True)
    experiment_session_maker = sessionmaker(EXPERIMENT_ENGINE, future=True)

    @contextmanager
    def begin(self) -> Iterator[Session]:
        with ExitStack() as stack:
            audit_session = stack.enter_context(self._audit_session_maker.begin())
            experiment_session = stack.enter_context(self.experiment_session_maker.begin())

            auditor = Auditor("gabriel", "experiment", audit_session=audit_session)
            event.listen(experiment_session, "after_flush", auditor.after_flush)
            event.listen(experiment_session, "before_flush", auditor.before_flush)

            yield experiment_session


SESSION = AuditedSession()
