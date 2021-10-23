from sqlalchemy import Column, Computed, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Number(Base):
    __tablename__ = "number"

    id = Column(Integer, primary_key=True)
    value = Column(Integer, nullable=False)
    doubled = Column(Integer, Computed("value + value", persisted=True))
    squared = Column(Integer, Computed("value * value", persisted=False))


class Person(Base):
    __tablename__ = "person"

    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    name = Column(String(64), nullable=False)
