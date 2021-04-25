from functools import lru_cache

from pydantic import BaseSettings


class BaseEnvironment(BaseSettings):
    class Config:
        env_file = ".env"


class Environment(BaseEnvironment):
    audit_url: str = "sqlite+pysqlite:///audit-fastapi.sqlite3"
    production_url: str = "sqlite+pysqlite:///production-fastapi.sqlite3"
    recovery_url: str = "sqlite+pysqlite:///recovery-fastapi.sqlite3"


@lru_cache
def get_environment() -> Environment:
    return Environment()
