from sqlalchemy import Column, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ChangeLog(Base):
    __tablename__ = "change_log"

    id = Column(Integer, primary_key=True)
    diff = Column(JSON, nullable=False)
    executed_at = Column(DateTime, nullable=False, server_default=func.now())
    new_values = Column(JSON, nullable=False)
    old_values = Column(JSON, nullable=False)
    table_name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)
