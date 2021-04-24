from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from resql.database.auditing import log_changes, log_queries
from resql.database.models import Base
from resql.database.models_audit import Base as AuditBase
from resql.database.models_recovery import Base as RecoveryBase


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


Base.metadata.create_all(EXPERIMENT_ENGINE)
AuditBase.metadata.create_all(AUDIT_ENGINE)
RecoveryBase.metadata.create_all(RECOVERY_ENGINE)

SESSION = sessionmaker(EXPERIMENT_ENGINE, future=True)

log_queries(of=EXPERIMENT_ENGINE, to=RECOVERY_ENGINE)
log_changes(of=SESSION, to=AUDIT_ENGINE)
