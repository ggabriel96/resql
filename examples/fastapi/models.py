from typing import Optional

from pydantic import BaseModel


class Model(BaseModel):
    class Config:
        orm_mode = True


class Country(Model):
    name: str
    population: Optional[int]


class CountryUpdate(BaseModel):
    name: Optional[str]
    population: Optional[int]
