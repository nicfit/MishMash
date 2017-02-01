import os
from pathlib import Path
import nicfit
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from sqlalchemy_utils.functions import (database_exists,
                                        create_database,
                                        drop_database)
from alembic import command
from alembic.config import Config

from .orm import TYPES, TABLES
from .orm import Base, Artist, Track, Album

DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                       "encoding": "utf8",
                       "echo": False,
                      }
DEFAULT_SESSION_ARGS = {
        }

log = nicfit.getLogger(__name__)

# FIXME: Remove once in nicfit.py
import contextlib
@contextlib.contextmanager
def cd(path):
    old_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)

def init(config, engine_args=None, session_args=None, trans_mgr=None):
    db_url = config.db_url
    alembic_d = Path(__file__).parent
    alembic_cfg = Config(str(alembic_d / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    log.debug("Checking for database '%s'" % db_url)
    if not database_exists(db_url):
        log.info("Creating database '%s'" % db_url)
        create_database(db_url, template="template0")

    log.debug("Connecting to database '%s'" % db_url)
    args = engine_args or DEFAULT_ENGINE_ARGS
    engine = create_engine(db_url, **args)
    engine.connect()

    args = session_args or DEFAULT_SESSION_ARGS
    if trans_mgr:
        args.update({"extension": trans_mgr})
    SessionMaker = sessionmaker(bind=engine, **args)

    for T in TYPES:
        T.metadata.bind = engine

    missing_tables = checkSchema(engine)
    if missing_tables:
        log.info("Creating database '%s'" % db_url)
        Base.metadata.create_all(engine)

        try:
            # Run extra table initialization any missing/new tables
            session = SessionMaker()
            for T in [t for t in TYPES if t.__table__ in missing_tables]:
                T.initTable(session, config)
            session.commit()
        except Exception as ex:
            session.rollback()
            raise
        finally:
            session.close()

        # Initialize Alembic with current revision hash.
        with cd(str(alembic_d)):
            command.stamp(alembic_cfg, "head")
    else:
        # Upgrade to head (i.e. this) revision, or no-op if they match
        with cd(str(alembic_d)):
            command.upgrade(alembic_cfg, "head")

    return engine, SessionMaker


def checkSchema(engine):
    missing_tables = []
    for table in TABLES:
        if not engine.has_table(table.name):
            log.debug(f"Missing {table.name}")
            missing_tables.append(table)
    return missing_tables


def dropAll(url):
    drop_database(url)


def search(session, query):
    flat_query = u"".join(query.split())

    artists = session.query(Artist).filter(
            or_(Artist.name.ilike(u"%%%s%%" % query),
                Artist.name.ilike(u"%%%s%%" % flat_query))
               ).all()
    albums = session.query(Album).filter(
            Album.title.ilike(u"%%%s%%" % query)).all()
    tracks = session.query(Track).filter(
            Track.title.ilike(u"%%%s%%" % query)).all()

    return dict(artists=artists,
                albums=albums,
                tracks=tracks)
