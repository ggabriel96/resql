from typing import Iterator

from pytest import fixture
from sqlalchemy.future import Engine
from sqlalchemy.orm import sessionmaker

from resql.change_log import map_default as map_default_change_log
from resql.query_log import map_default as map_default_query_log
from tests import database
from tests.models import Base as ProductionBase
from tests.settings import Environment
from tests.utils import Registries, truncate_all


@fixture(name="env", scope="session")
def _env() -> Environment:
    return Environment()


@fixture(name="init_database", scope="session")
def _init_database(env: Environment) -> None:
    database.init_engines(env)


@fixture(name="registries", scope="session")
def _registries(init_database: None) -> Registries:  # pylint: disable=unused-argument
    return Registries(
        audit=map_default_change_log(),
        recovery=map_default_query_log(),
    )


@fixture(name="audit_engine", scope="function")
def _audit_engine(registries: Registries) -> Iterator[Engine]:
    registries.audit.metadata.create_all(database.AUDIT_ENGINE)
    yield database.AUDIT_ENGINE  # type: ignore[misc]
    truncate_all(database.AUDIT_ENGINE)  # type: ignore[arg-type]


@fixture(name="recovery_engine", scope="function")
def _recovery_engine(registries: Registries) -> Iterator[Engine]:
    registries.recovery.metadata.create_all(database.RECOVERY_ENGINE)
    yield database.RECOVERY_ENGINE  # type: ignore[misc]
    truncate_all(database.RECOVERY_ENGINE)  # type: ignore[arg-type]


@fixture(name="production_engine", scope="function")
def _production_engine(init_database: None) -> Iterator[Engine]:  # pylint: disable=unused-argument
    ProductionBase.metadata.create_all(database.PRODUCTION_ENGINE)
    yield database.PRODUCTION_ENGINE  # type: ignore[misc]
    truncate_all(database.PRODUCTION_ENGINE)  # type: ignore[arg-type]


@fixture(name="audit_mksession", scope="function")
def _audit_mksession(audit_engine: Engine) -> sessionmaker:
    return sessionmaker(audit_engine, expire_on_commit=False, future=True)


@fixture(name="recovery_mksession", scope="function")
def _recovery_mksession(recovery_engine: Engine) -> sessionmaker:
    return sessionmaker(recovery_engine, expire_on_commit=False, future=True)


@fixture(name="production_mksession", scope="function")
def _production_mksession(production_engine: Engine) -> sessionmaker:
    return sessionmaker(production_engine, expire_on_commit=False, future=True)
