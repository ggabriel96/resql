from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class QueryLog(Base):
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True)
    dialect_description = Column(String(64), nullable=False)
    executed_at = Column(DateTime, nullable=False, server_default=func.now())
    parameters = Column(JSON, nullable=True)
    statement = Column(Text, nullable=False)
    type = Column(String(32), nullable=False)
