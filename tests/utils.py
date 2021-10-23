import datetime as dt
from dataclasses import dataclass
from typing import Any, cast

import rapidjson
from sqlalchemy import MetaData
from sqlalchemy.future import Engine
from sqlalchemy.orm import registry


def from_json(obj: str) -> Any:
    return rapidjson.loads(obj, datetime_mode=rapidjson.DM_ISO8601, uuid_mode=rapidjson.UM_CANONICAL)


def now_in_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def to_json(obj: Any) -> str:
    return cast(str, rapidjson.dumps(obj, datetime_mode=rapidjson.DM_ISO8601, uuid_mode=rapidjson.UM_CANONICAL))


def truncate_all(engine: Engine) -> None:
    meta = MetaData()
    meta.reflect(bind=engine)
    with engine.begin() as conn:  # type: ignore[no-untyped-call]
        for table in reversed(meta.sorted_tables):
            conn.execute(table.delete())


@dataclass
class Registries:
    audit: registry
    recovery: registry
