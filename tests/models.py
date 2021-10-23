from sqlalchemy import Column, Computed, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Number(Base):
    __tablename__ = "number"

    id = Column(Integer, primary_key=True)
    value = Column(Integer, nullable=False)
    doubled = Column(Integer, Computed("value + value", persisted=True))
    # there was a `persisted=False` column here, but PostgreSQL doesn't support it,
    # so we gotta find a way to eventually test that too.


class Person(Base):
    __tablename__ = "person"

    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    name = Column(String(64), nullable=False)
