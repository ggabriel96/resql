import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import JSON, Column, Integer, MetaData, String, Table
from sqlalchemy.orm import registry
from sqlalchemy_utc import UtcDateTime


@dataclass
class ChangeLog:
    id: int = field(init=False)
    diff: dict[str, Any]
    executed_at: dt.datetime
    extra: Optional[dict[str, Any]]
    record_id: int
    table_name: str
    type: str


def default_table(metadata: MetaData) -> Table:
    return Table(
        "change_log",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("diff", JSON, nullable=False),
        Column("executed_at", UtcDateTime, nullable=False),
        Column("extra", JSON, nullable=True),
        Column("record_id", Integer, nullable=False),
        Column("table_name", String(128), nullable=False),
        Column("type", String(32), nullable=False),
    )


def map_default() -> registry:
    mapper_registry = registry()
    mapper_registry.map_imperatively(ChangeLog, default_table(mapper_registry.metadata))
    return mapper_registry
