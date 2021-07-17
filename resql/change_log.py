import datetime as dt
import enum
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import JSON, Column, Enum, Integer, MetaData, String, Table
from sqlalchemy.orm import registry
from sqlalchemy_utc import UtcDateTime

from resql.util import enum_values


class OpType(str, enum.Enum):
    DELETE = "Delete"
    INSERT = "Insert"
    UPDATE = "Update"


@dataclass
class ChangeLog:
    id: int = field(init=False)
    diff: dict[str, Any]
    executed_at: dt.datetime
    extra: Optional[dict[str, Any]]
    record_id: int
    table_name: str
    type: OpType


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
        Column("type", Enum(OpType, values_callable=enum_values), nullable=False),
    )


def map_default() -> registry:
    mapper_registry = registry()
    mapper_registry.map_imperatively(ChangeLog, default_table(mapper_registry.metadata))
    return mapper_registry
