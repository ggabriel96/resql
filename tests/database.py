from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_utc import UtcDateTime

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


@compiles(UtcDateTime, "mysql")  # type: ignore[misc]
def compile_utcdatetime(*_: Any, **__: Any) -> str:
    """
    Related docs:
    - https://dev.mysql.com/doc/refman/8.0/en/fractional-seconds.html
    - https://docs.sqlalchemy.org/en/14/core/custom_types.html#overriding-type-compilation
    - https://docs.sqlalchemy.org/en/14/core/compiler.html#changing-the-default-compilation-of-existing-constructs
    """
    return "DATETIME(6)"
