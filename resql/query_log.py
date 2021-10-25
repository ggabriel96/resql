import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, Text
from sqlalchemy.orm import registry
from sqlalchemy_utc import UtcDateTime


@dataclass
class QueryLog:
    id: int = field(init=False)
    dialect_description: str
    executed_at: dt.datetime
    extra: Optional[dict[str, Any]]
    parameters: list[dict[str, Any]]
    statement: str
    type: str


def default_table(metadata: MetaData) -> Table:
    return Table(
        "query_log",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("dialect_description", String(64), nullable=False),
        Column("executed_at", UtcDateTime, nullable=False),
        Column("extra", JSON, nullable=True),
        Column("parameters", JSON, nullable=True),
        Column("statement", Text, nullable=False),
        Column("type", String(32), nullable=False),
    )


def map_default() -> registry:
    mapper_registry = registry()
    mapper_registry.map_imperatively(QueryLog, default_table(mapper_registry.metadata))
    return mapper_registry
