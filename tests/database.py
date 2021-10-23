from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from tests.settings import Environment
from tests.utils import from_json, to_json

AUDIT_ENGINE: Engine
RECOVERY_ENGINE: Engine
PRODUCTION_ENGINE: Engine


def init_engines(env: Environment) -> None:
    global AUDIT_ENGINE, RECOVERY_ENGINE, PRODUCTION_ENGINE  # pylint: disable=global-statement
    AUDIT_ENGINE = create_engine(
        env.audit_url,
        echo=True,
        future=True,
        json_deserializer=from_json,
        json_serializer=to_json,
        logging_name="AUDITING",
    )
    RECOVERY_ENGINE = create_engine(
        env.recovery_url,
        echo=True,
        future=True,
        json_deserializer=from_json,
        json_serializer=to_json,
        logging_name="RECOVERY",
    )
    PRODUCTION_ENGINE = create_engine(
        env.production_url,
        echo=True,
        future=True,
        json_deserializer=from_json,
        json_serializer=to_json,
        logging_name="PRODUCTN",
    )
