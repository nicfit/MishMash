# -*- coding: utf-8 -*-
import uuid
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections import namedtuple
import unittest
from pyramid import testing
import mishmash.database

TestDatabase = namedtuple("TestDatabase", ["url", "engine", "SessionMaker"])


@pytest.fixture(scope="session",
                params=["sqlite", "postgresql"])
def database(request):
    if request.param == "sqlite":
        db_file = NamedTemporaryFile(suffix=".sqlite", delete=False)
        db_file.close()
        db_url = f"sqlite:///{db_file.name}"
        engine, SessionMaker = mishmash.database.init(db_url)
    elif request.param == "postgresql":
        uid = str(uuid.uuid4())
        db_url = f"postgresql://mishmash@localhost/MMTEST_{uid}"
        engine, SessionMaker = mishmash.database.init(db_url)
    else:
        assert not("unhandled db: " + request.param)

    yield TestDatabase(url=db_url, engine=engine, SessionMaker=SessionMaker)

    if request.param == "sqlite":
        Path(db_file.name).unlink()
    else:
        mishmash.database.dropAll(db_url)


@pytest.fixture
def session(database):
    session = database.SessionMaker()
    yield session
    session.rollback()
    session.close()


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.engine,
         cls.session) = mishmash.database.init(settings['sqlalchemy.url'],
                                               drop_all=True)

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request=request)
        self.config.add_settings(settings)

    def tearDown(self):
        testing.tearDown()
