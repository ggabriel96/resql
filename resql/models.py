from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import declarative_base

AuditingBase = declarative_base()
RecoveryBase = declarative_base()


class ChangeLog(AuditingBase):
    __tablename__ = "change_log"

    id = Column(Integer, primary_key=True)
    diff = Column(JSON, nullable=False)
    executed_at = Column(DateTime, nullable=False, server_default=func.now())
    table_name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)


class QueryLog(RecoveryBase):
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True)
    dialect_description = Column(String(64), nullable=False)
    executed_at = Column(DateTime, nullable=False, server_default=func.now())
    parameters = Column(JSON, nullable=True)
    statement = Column(Text, nullable=False)
    type = Column(String(32), nullable=False)
