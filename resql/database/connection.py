from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from resql.database.auditing import log_changes, log_queries
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

SESSION = sessionmaker(EXPERIMENT_ENGINE, future=True)

log_queries(of=EXPERIMENT_ENGINE, to=RECOVERY_ENGINE)
log_changes(of=SESSION, to=AUDIT_ENGINE)
