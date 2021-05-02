import datetime as dt
from typing import Iterator

from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.models import AuditingBase, RecoveryBase
from tests.models import Base as ProductionBase
from tests.settings import Environment
from tests.utils import truncate_all


@fixture(name="env", scope="session")
def _env() -> Environment:
    return Environment()


@fixture(name="audit_engine", scope="function")
def _audit_engine(env: Environment) -> Iterator[Engine]:
    audit_engine = create_engine(
        env.audit_url,
        echo=True,
        future=True,
        logging_name="AUDITING",
    )
    AuditingBase.metadata.create_all(audit_engine)
    yield audit_engine  # type: ignore[misc]
    truncate_all(audit_engine)  # type: ignore[arg-type]


@fixture(name="audit_now", scope="function")
def _audit_now(audit_engine: Engine) -> dt.datetime:
    if "postgresql" in audit_engine.dialect.dialect_description:
        return dt.datetime.now(dt.timezone.utc)
    return dt.datetime.utcnow().replace(microsecond=0)


@fixture(name="recovery_engine", scope="function")
def _recovery_engine(env: Environment) -> Iterator[Engine]:
    recovery_engine = create_engine(
        env.recovery_url,
        echo=True,
        future=True,
        logging_name="RECOVERY",
    )
    RecoveryBase.metadata.create_all(recovery_engine)
    yield recovery_engine  # type: ignore[misc]
    truncate_all(recovery_engine)  # type: ignore[arg-type]


@fixture(name="recovery_now", scope="function")
def _recovery_now(recovery_engine: Engine) -> dt.datetime:
    if "postgresql" in recovery_engine.dialect.dialect_description:
        return dt.datetime.now(dt.timezone.utc)
    return dt.datetime.utcnow().replace(microsecond=0)


@fixture(name="production_engine", scope="function")
def _production_engine(env: Environment) -> Iterator[Engine]:
    production_engine = create_engine(
        env.production_url,
        echo=True,
        future=True,
        logging_name="PRODUCTN",
    )
    ProductionBase.metadata.create_all(production_engine)
    yield production_engine  # type: ignore[misc]
    truncate_all(production_engine)  # type: ignore[arg-type]


@fixture(name="audit_mksession", scope="function")
def _audit_mksession(audit_engine: Engine) -> sessionmaker:
    return sessionmaker(audit_engine, future=True)


@fixture(name="recovery_mksession", scope="function")
def _recovery_mksession(recovery_engine: Engine) -> sessionmaker:
    return sessionmaker(recovery_engine, future=True)


@fixture(name="production_mksession", scope="function")
def _production_mksession(production_engine: Engine) -> sessionmaker:
    return sessionmaker(production_engine, future=True)
