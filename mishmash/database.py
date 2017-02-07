from pathlib import Path
import nicfit
from nicfit.util import cd
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from sqlalchemy_utils.functions import (database_exists,
                                        create_database,
                                        drop_database)
from alembic import command
from alembic.config import Config

from .orm import TYPES
from .orm import Artist, Track, Album

DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                       "encoding": "utf8",
                       "echo": False,
                      }
DEFAULT_SESSION_ARGS = {
        }

log = nicfit.getLogger(__name__)


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

    # Upgrade to head (i.e. this) revision, or no-op if they match
    with cd(str(alembic_d)):
        command.upgrade(alembic_cfg, "head")

    return engine, SessionMaker


def dropAll(url):
    drop_database(url)


def search(session, query):
    # FIXME
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
