from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound


def sqlalchemy_not_found_exception(_: Request, __: NoResultFound) -> JSONResponse:
    return JSONResponse({"detail": "Not Found"}, status_code=status.HTTP_404_NOT_FOUND)
