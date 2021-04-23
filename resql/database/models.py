from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import registry

mapper_registry = registry()


@mapper_registry.mapped
class Person:
    __tablename__ = "person"

    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    name = Column(String, nullable=False)
