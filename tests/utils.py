import datetime as dt

from sqlalchemy import MetaData
from sqlalchemy.future import Engine


def now_in_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def truncate_all(engine: Engine) -> None:
    meta = MetaData()
    meta.reflect(bind=engine)
    with engine.begin() as conn:  # type: ignore[no-untyped-call]
        for table in reversed(meta.sorted_tables):
            conn.execute(table.delete())
