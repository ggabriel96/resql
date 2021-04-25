from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from examples.fastapi.database import begin_session
from examples.fastapi.database.models import Person as PersonDB
from examples.fastapi.models import Person, PersonInsert, PersonUpdate


router = APIRouter(prefix="/person")


@router.get(
    "/{person_id}",
    tags=["person"],
    response_model=Person,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def get(person_id: int, db: Session = Depends(begin_session)) -> Person:
    person = db.execute(select(PersonDB).where(PersonDB.id == person_id)).scalar_one()
    return Person.from_orm(person)


@router.post("", tags=["person"], response_model=Person)
def insert(person_data: PersonInsert, db: Session = Depends(begin_session)) -> Person:
    person = PersonDB(**person_data.dict())
    db.add(person)
    db.flush()  # flushing so we get back the ID of the model
    return Person.from_orm(person)


@router.patch("/{person_id}", tags=["person"], response_model=Person)
def update(person_id: int, person_data: PersonUpdate, db: Session = Depends(begin_session)) -> Person:
    person = db.execute(select(PersonDB).where(PersonDB.id == person_id)).scalar_one()
    for key, value in person_data.dict(exclude_none=True).items():
        setattr(person, key, value)
    return Person.from_orm(person)
