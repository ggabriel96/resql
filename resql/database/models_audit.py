from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.mapped
class ChangeLog:
    __tablename__ = "change_log"

    id = Column(Integer, primary_key=True)
    diff = Column(JSON, nullable=False)
    executed_at = Column(DateTime, nullable=False)
    new_values = Column(JSON, nullable=False)
    old_values = Column(JSON, nullable=False)
    table_name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)
