from sqlalchemy import Column, Integer, JSON, String, Text
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.mapped
class QueryLog:
    __tablename__ = "query_log"
    # add some engine identifier (e.g. pymysql, psycopg2, etc)

    id = Column(Integer, primary_key=True)
    parameters = Column(JSON, nullable=True)
    statement = Column(Text, nullable=False)
    type = Column(String(32), nullable=False)
