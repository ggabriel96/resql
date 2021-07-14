from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from tests.settings import Environment

AUDIT_ENGINE: Engine
RECOVERY_ENGINE: Engine
PRODUCTION_ENGINE: Engine


def init_engines(env: Environment) -> None:
    global AUDIT_ENGINE, RECOVERY_ENGINE, PRODUCTION_ENGINE  # pylint: disable=global-statement
    AUDIT_ENGINE = create_engine(env.audit_url, echo=True, future=True, logging_name="AUDITING")
    RECOVERY_ENGINE = create_engine(env.recovery_url, echo=True, future=True, logging_name="RECOVERY")
    PRODUCTION_ENGINE = create_engine(env.production_url, echo=True, future=True, logging_name="PRODUCTN")
