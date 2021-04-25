from fastapi import FastAPI
from sqlalchemy.exc import NoResultFound

from examples.fastapi import error_handlers
from examples.fastapi.endpoints import countries
from examples.fastapi.database import init_from_env
from examples.fastapi.settings import get_environment

app = FastAPI(name="example", version="0.1.0")

app.include_router(countries.router)

app.add_exception_handler(NoResultFound, error_handlers.sqlalchemy_not_found_exception)


@app.on_event("startup")
def startup() -> None:
    init_from_env(get_environment())
