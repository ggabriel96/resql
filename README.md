# resql

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![codecov](https://codecov.io/gh/ggabriel96/resql/branch/main/graph/badge.svg?token=AOVOWTNSMW)](https://codecov.io/gh/ggabriel96/resql)

resql (pronounced like "rescue") is a database auditing and recovery library based on SQLAlchemy.
It mainly provides two things: a way to register changes to objects (the change log), and a way to register executed queries (the query log).

**This is way too early in development, so don't use it in production.**
For example, the recovery features, like restoring a database using the logged queries, are not yet available.
Additionally, there are many, many tests yet to be implemented, and the interface is not stable.

## The change log

As the name implies, the change log focuses on establishing a complete history of an object's changes.
It currently registers the following information:

- the name of the table in which it occurred
- the primary key (PK) of the object that changed (in JSON, so we support generic PKs)
- the diff of the change, in JSON
- the type of the change (insert, update, or delete)
- the date and time of the change
- any extra information provided during setup

To setup change logs, simply call `log_changes`:

```python
from resql.auditing import log_changes

log_changes(of=session, to=audit_engine)
```

It is just a shortcut to creating a `ChangeLogger` and adding the event listener.
The function signature is as follows:

```python
def log_changes(
    *,
    of: Union[Session, sessionmaker],
    to: Engine,
    extra: Optional[dict[str, Any]] = None,
) -> ChangeLogger
```

## The query log

The main goal of the query log is to aid database recovery by logging every query that executed.
In order to do this, it registers the following information:

- the type of the query, taken directly from SQLAlchemy's: `Select`, `Insert`, `Update`, etc.
- the dialect of the query, e.g. `sqlite+pysqlite`
- the compiled statement that was executed
- the compiled parameters of the statement
- the date and time the query was executed
- any extra information provided during setup

With this data, one should be able to programmatically re-run these queries again from a given starting point.

To setup query logs, simply call `log_queries`:

```python
from resql.auditing import log_queries

log_queries(of=production_engine, to=recovery_engine)
```

Similarly to `log_changes`, it is just a shortcut to creating a `QueryLogger` and adding the event listener.
The function signature is as follows:

```python
def log_queries(
    *,
    of: Union[Engine, Connection],
    to: Engine,
    extra: Optional[dict[str, Any]] = None,
) -> QueryLogger
```

## The `extra` parameter

The `extra` parameter is the extra information that will be added to each log.
Note that the change log can be registered on a `Session` or a `sessionmaker`, and the query log can be registered on an `Engine` or a `Connection`.
Registering them on a `Session` or a `Connection`, respectively, adds more flexibility to what `extra`s will be saved, since one could want them to vary under certain conditions.
One possible use case is to add information about the current user that is logged in and causing these changes or queries.
Using them on `sessionmaker` or `Engine` is more like global loggers.
