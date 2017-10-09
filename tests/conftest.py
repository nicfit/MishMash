import uuid
import shutil
import tempfile
import pytest
from pathlib import Path
from collections import namedtuple
from tempfile import NamedTemporaryFile

import mishmash.database
from .factories import (Mp3AudioFileFactory, TagFactory, AlbumFactory,
                        LibraryFactory)

TestDatabase = namedtuple("TestDatabase", ["url", "engine", "SessionMaker"])


@pytest.fixture(scope="session",
                params=["sqlite", "postgresql"])
def database(request, pg_server):
    if request.param == "sqlite":
        db_file = NamedTemporaryFile(suffix=".sqlite", delete=False)
        db_file.close()
        db_url = f"sqlite:///{db_file.name}"
    elif request.param == "postgresql":
        db_url = "postgresql://{user}:{password}@{host}:{port}/{database}"\
                 .format(**pg_server["params"])
    else:
        assert not("unhandled db: " + request.param)
        return

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


@pytest.fixture(scope="session", autouse=True)
def mishmash_tempdir():
    global TEMP_DIR

    temp_d = tempfile.TemporaryDirectory()
    TEMP_DIR = temp_d

    yield Path(temp_d.name)

    if Path(temp_d.name).exists():
        temp_d.cleanup()


@pytest.fixture(scope="function")
def mp3audiofile(mishmash_tempdir):
    path = NamedTemporaryFile(dir=str(mishmash_tempdir), suffix=".mp3")
    mp3_file = Mp3AudioFileFactory(tag=TagFactory())

    yield mp3_file

    Path(mp3_file.path).unlink()


def _tempCopy(src, dest_dir):
    testfile = Path(str(dest_dir)) / "{}.mp3".format(uuid.uuid4())
    shutil.copyfile(str(src), str(testfile))
    return testfile
