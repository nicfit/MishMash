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
import os

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import scoped_session, sessionmaker

from . import log
from .orm import TYPES, TABLES, ENUMS
from .orm import Artist, Track, Album, VARIOUS_ARTISTS_NAME, Meta

SUPPORTED_DB_TYPES = ["sqlite", "postgresql", "oracle"]

DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                       "encoding": "utf8",
                       "echo": False,
                      }
DEFAULT_SESSION_ARGS = {"autocommit": True,
                        "autoflush": False,
                       }


def init(uri, engine_args=None, session_args=None):
    log.debug("Connecting to database '%s'" % uri)

    args = engine_args or DEFAULT_ENGINE_ARGS
    engine = create_engine(uri, **args)
    engine.connect()

    args = session_args or DEFAULT_SESSION_ARGS
    Session = scoped_session(sessionmaker(**args))
    Session.configure(bind=engine)

    for T in TYPES:
        T.metadata.bind = engine

    return engine, Session


def check(engine):
    missing_tables = []
    for table in TABLES:
        if not engine.has_table(table.name):
            missing_tables.append(table)

    if missing_tables:
        raise MissingSchemaException(missing_tables)


def create(session, tables=None):
    tables = tables or TABLES

    for table in tables:
        log.debug("Creating table '%s'..." % table)
        table.create()
        for T in TYPES:
            if T.__tablename__ == table.name:
                with session.begin():
                    T.initTable(session)

def dropAll(engine):

    for dbo_list in [TABLES, ENUMS]:
        tmp = list(dbo_list)
        tmp.reverse()

        for dbo in tmp:
            try:
                log.debug("Dropping '%s'" % dbo)
                dbo.drop(bind=engine)
            except OperationalError as ex:
                log.debug(str(ex))


def makeDbUri(db_type, name, host=None, port=None, username=None,
              password=None):
    if not (db_type and name):
        raise ValueError("Database type and name required")

    uri = None
    if db_type == "postgresql":
        port = 5432 if not port else port
        if not (host and port and username and password):
            raise ValueError("host, port, username, and password required")
        uri = "%s://%s:%s@%s:%d/%s" % (db_type, username, password,
                                       host, int(port), name)

    elif db_type == "sqlite":
        uri = "%s:///%s" % (db_type, name)
    else:
        raise ValueError("Unsupported DB type '%s'. Options are %s" %
                         (str(db_type), str(SUPPORTED_DB_TYPES)))

    return uri


class MissingSchemaException(Exception):
    def __init__(self, missing_tables):
        super(MissingSchemaException, self).__init__("missing tables")
        self.tables = missing_tables

