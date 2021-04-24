from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.database.models_audit import Base as AuditBase
from resql.database.models_recovery import Base as RecoveryBase
from tests.models import Base as ProductionBase
from tests.settings import Environment


@fixture(name="env", scope="session")
def _env() -> Environment:
    return Environment()


@fixture(name="audit_engine", scope="session")
def _audit_engine(env: Environment) -> Engine:
    audit_engine = create_engine(
        env.audit_url,
        echo=True,
        future=True,
        logging_name="AUDITING",
    )
    AuditBase.metadata.create_all(audit_engine)
    return audit_engine


@fixture(name="recovery_engine", scope="session")
def _recovery_engine(env: Environment) -> Engine:
    recovery_engine = create_engine(
        env.recovery_url,
        echo=True,
        future=True,
        logging_name="RECOVERY",
    )
    RecoveryBase.metadata.create_all(recovery_engine)
    return recovery_engine


@fixture(name="production_engine", scope="session")
def _production_engine(env: Environment) -> Engine:
    production_engine = create_engine(
        env.production_url,
        echo=True,
        future=True,
        logging_name="PRODUCTN",
    )
    ProductionBase.metadata.create_all(production_engine)
    return production_engine


@fixture(name="audit_mksession", scope="session")
def _audit_mksession(audit_engine: Engine) -> sessionmaker:
    return sessionmaker(audit_engine, future=True)


@fixture(name="recovery_mksession", scope="session")
def _recovery_mksession(recovery_engine: Engine) -> sessionmaker:
    return sessionmaker(recovery_engine, future=True)


@fixture(name="production_mksession", scope="session")
def _production_mksession(production_engine: Engine) -> sessionmaker:
    return sessionmaker(production_engine, future=True)
