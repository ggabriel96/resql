from sqlalchemy import select, text

from resql.database.connection import SESSION
from resql.database.models import Person

with SESSION.begin() as session:
    person = Person(name="Gabriel")
    session.add(person)

with SESSION.begin() as session:
    person = session.execute(select(Person).where(Person.id == 1)).scalar_one()
    person.name = "Gabriel Galli"
    # raise Exception("nope")

with SESSION.begin() as session:
    r = session.execute(text("select * from person"))
    print(r)
