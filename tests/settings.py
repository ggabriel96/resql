from pydantic import BaseSettings


class BaseEnvironment(BaseSettings):
    class Config:
        env_file = ".env"


class Environment(BaseEnvironment):
    audit_url: str = "sqlite+pysqlite:///audit.sqlite3"
    production_url: str = "sqlite+pysqlite:///production.sqlite3"
    recovery_url: str = "sqlite+pysqlite:///recovery.sqlite3"
