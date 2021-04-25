from typing import Optional

from pydantic import BaseModel


class Model(BaseModel):
    class Config:
        orm_mode = True


class Person(Model):
    id: int
    age: Optional[int]
    name: str


class PersonInsert(BaseModel):
    age: Optional[int]
    name: str


class PersonUpdate(BaseModel):
    age: Optional[int]
    name: Optional[str]
