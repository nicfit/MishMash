################################################################################
#  Copyright (C) 2013  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import scoped_session, sessionmaker

from sqlalchemy_utils.functions import (database_exists,
                                        create_database,
                                        drop_database)

from . import log
from .orm import TYPES, TABLES
from .orm import Base, Artist, Track, Album

DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                       "encoding": "utf8",
                       "echo": False,
                      }
DEFAULT_SESSION_ARGS = {
        }


def init(config, engine_args=None, session_args=None, trans_mgr=None):
    url = config.db_url

    log.debug("Checking for database '%s'" % url)
    if not database_exists(url):
        log.info("Creating database '%s'" % url)
        create_database(url, template="template0")

    log.debug("Connecting to database '%s'" % url)
    args = engine_args or DEFAULT_ENGINE_ARGS
    engine = create_engine(url, **args)
    engine.connect()

    args = session_args or DEFAULT_SESSION_ARGS
    if trans_mgr:
        import transaction
        args.update({"extension": trans_mgr})
    SessionMaker = sessionmaker(bind=engine, **args)

    for T in TYPES:
        T.metadata.bind = engine

    session= SessionMaker()
    try:
        try:
            log.debug("Checking database schema '%s'" % url)
            checkSchema(engine)
        except MissingSchemaException as ex:
            log.info("Creating database schema '%s'" % url)
            Base.metadata.create_all(engine)
            for T in TYPES:
                # Run extra table initialization
                T.initTable(session, config)

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
