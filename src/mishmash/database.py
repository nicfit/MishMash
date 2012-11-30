# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2012  Travis Shirk <travis@pobox.com>
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
import sqlalchemy as sql

from .orm import TYPES, TABLES, LABELS
from .orm import Track, Artist, Album
from . import log


_SUPORTED_DB_TYPES = ["sqlite", "postgres", "oracle"]

class Database(object):
    DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                           "encoding": "utf8",
                          }

    def __init__(self, db_type, name, host=None, port=None,
                 username=None, password=None, do_create=False,
                 do_upgrage=False):

        self._db_uri = makeDbUri(db_type, name, host=host, port=port,
                                 username=username, password=password)
        self._engine = sql.create_engine(self._db_uri,
                                         **self.DEFAULT_ENGINE_ARGS)
        try:
            log.info("Connecting to database '%s'" % self._db_uri)
            self._engine.connect()
        except sql.exc.OperationalError as ex:
            raise ConnectException(str(ex))

        # Make the type creating sessions.
        self.Session = sql.orm.sessionmaker(bind=self._engine,
                                            autocommit=True, autoflush=False)

        # Map the ORM
        for T in TYPES:
            T.metadata.bind = self._engine

        # Test the schema
        missing_tables = []
        for table in TABLES:
            if not self._engine.has_table(table.name):
                missing_tables.append(table)

        if missing_tables and not do_create:
            raise MissingSchemaException([str(t) for t in missing_tables])

        for table in missing_tables:
            log.info("Creating table '%s'..." % table)
            table.create()
            for T in TYPES:
                if T.__tablename__ == table.name:
                    session = self.Session()
                    with session.begin():
                        T.initTable(session)

        # Once schema version is in 'meta' do upgrades.
        # TODO

    def dropAllTables(self):
        log.warn("Dropping all database tables!")
        tables = list(TABLES)
        tables.reverse()
        for table in tables:
            table.drop()


def makeDbUri(db_type, name, host=None, port=None,
              username=None, password=None):
        assert(db_type and name)

        uri = None
        if db_type == "postgres":
            port = 5432 if not port else port
            assert(host and port and username and password)
            uri = "%s://%s:%s@%s:%d/%s" % (db_type, username, password,
                                           host, int(port), name)

        elif db_type == "sqlite":
            uri = "%s:///%s" % (db_type, name)
        elif db_type == "oracle":
            assert(username and password)
            # Name is the DSN
            uri = "%s://%s:%s@%s" % (db_type, username, password, name)
        else:
            raise ValueError("Unsupported DB type '%s'. Options are %s" %
                             (str(db_type), str(_SUPORTED_DB_TYPES)))

        return uri


class ConnectException(Exception):
    pass

class MissingSchemaException(Exception):
    def __init__(self, missing_tables):
        super(MissingSchemaException, self).__init__("missing tables")
        self.tables = missing_tables

class UpgradeRequiredException(Exception):
    pass


class Synchronizer(object):
    def __init__(self, db):
        self.db = db
