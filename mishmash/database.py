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


def init(config, engine_args=None, session_args=None, trans_mgr=None):
    db_url = config.db_url

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
        import transaction
        args.update({"extension": trans_mgr})
    SessionMaker = sessionmaker(bind=engine, **args)

    for T in TYPES:
        T.metadata.bind = engine

    session = SessionMaker()
    alembic_init = False
    try:
        try:
            log.debug("Checking database schema '%s'" % db_url)
            checkSchema(engine)
        except MissingSchemaException as ex:
            log.info("Creating database schema '%s'" % db_url)
            Base.metadata.create_all(engine)
            for T in TYPES:
                # Run extra table initialization
                T.initTable(session, config)

            alembic_init = True

        if trans_mgr:
            transaction.commit()
        else:
            session.commit()
    except Exception as ex:
        if trans_mgr:
            transaction.abort()
        else:
            session.rollback()
        raise
    finally:
        session.close()

    if alembic_init:
        alembic_d = Path(__file__).parent
        alembic_cfg = Config(str(alembic_d / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        cwd = os.getcwd()
        try:
            os.chdir(str(alembic_d))
            command.stamp(alembic_cfg, "head")
        finally:
            os.chdir(cwd)

    return engine, SessionMaker


def checkSchema(engine):
    missing_tables = []
    for table in TABLES:
        if not engine.has_table(table.name):
            missing_tables.append(table)

    if missing_tables:
        raise MissingSchemaException(missing_tables)


def dropAll(url):
    drop_database(url)


class MissingSchemaException(Exception):
    def __init__(self, missing_tables):
        super(MissingSchemaException, self).__init__("missing tables")
        self.tables = missing_tables


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
