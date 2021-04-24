from sqlalchemy import MetaData
from sqlalchemy.future import Engine


def truncate_all(engine: Engine) -> None:
    meta = MetaData()
    meta.reflect(bind=engine)
    with engine.begin() as conn:
        for table in reversed(meta.sorted_tables):
            conn.execute(table.delete())
