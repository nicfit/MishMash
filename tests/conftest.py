# -*- coding: utf-8 -*-
import uuid
import pytest
from pathlib import Path
from collections import namedtuple
from tempfile import NamedTemporaryFile
import mishmash.database

TestDatabase = namedtuple("TestDatabase", ["url", "engine", "SessionMaker"])


@pytest.fixture(scope="session",
                params=["sqlite", "postgresql"])
def database(request):
    if request.param == "sqlite":
        db_file = NamedTemporaryFile(suffix=".sqlite", delete=False)
        db_file.close()
        db_url = f"sqlite:///{db_file.name}"
    elif request.param == "postgresql":
        uid = str(uuid.uuid4())
        db_url = f"postgresql://postgres@localhost/MMTEST_{uid}"
    else:
        assert not("unhandled db: " + request.param)

    engine, SessionMaker, connection = mishmash.database.init(db_url)

    # Outermost transaction that is always rolled back
    trans = connection.begin()
    yield TestDatabase(url=db_url, engine=engine, SessionMaker=SessionMaker)

    # ... teardown
    trans.rollback()
    connection.close()

    if request.param == "sqlite":
        Path(db_file.name).unlink()
    else:
        mishmash.database.dropAll(db_url)


@pytest.fixture
def session(database):
    session = database.SessionMaker()
    yield session
    # ... teardown
    session.rollback()
    session.close()
