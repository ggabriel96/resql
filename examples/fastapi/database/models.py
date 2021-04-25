from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Country(Base):
    __tablename__ = "country"

    name = Column(String, primary_key=True)
    population = Column(Integer, nullable=True)
