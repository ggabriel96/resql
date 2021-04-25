from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from examples.fastapi.database import begin_session
from examples.fastapi.database.models import Country as DBCountry
from examples.fastapi.models import Country, CountryUpdate


router = APIRouter(prefix="/countries")


@router.get(
    "/{country_name}",
    tags=["country"],
    response_model=Country,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def get(country_name: str, db: Session = Depends(begin_session)) -> Country:
    country = db.execute(select(DBCountry).where(DBCountry.name == country_name)).scalar_one()
    return Country.from_orm(country)


@router.post("", tags=["country"], response_model=Country)
def insert(country_data: Country, db: Session = Depends(begin_session)) -> Country:
    country = DBCountry(**country_data.dict())
    db.add(country)
    # although not _actually_ needed for this model,
    # doing a flush so we get back stuff from DB
    db.flush()
    return Country.from_orm(country)


@router.patch("/{country_name}", tags=["country"], response_model=Country)
def update(country_name: str, country_data: CountryUpdate, db: Session = Depends(begin_session)) -> Country:
    country = db.execute(select(DBCountry).where(DBCountry.name == country_name)).scalar_one()
    for key, value in country_data.dict(exclude_unset=True).items():
        setattr(country, key, value)
    return Country.from_orm(country)
