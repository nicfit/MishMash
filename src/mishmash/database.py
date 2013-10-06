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
import os
import sqlalchemy as sql

from .orm import TYPES, TABLES, LABELS, VARIOUS_ARTISTS_NAME, ENUMS
from .orm import Track, Artist, Album, Meta
from . import log


SUPPORTED_DB_TYPES = ["sqlite", "postgresql", "oracle"]


class DBInfo(object):
    def __init__(self, db_type=None, name=None, host=None, port=None,
                 username=None, password=None, uri=None, dbengine=None,
                 dbsession=None):
        self.db_type = db_type

        if name:
            self.name = name
        elif db_type == "sqlite":
            self.name = os.path.expandvars("${HOME}/mishmash.db")
        else:
            self.name = "mishmash"

        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.uri = uri
        self.dbengine = dbengine
        self.dbsession = dbsession

        # Must supply a dbengine if supplying a dbsession
        assert ((not dbengine and not dbsession) or (dbengine and dbsession) or
                (dbengine and not dbsession))


class Database(object):
    DEFAULT_ENGINE_ARGS = {"convert_unicode": True,
                           "encoding": "utf8",
                           "echo": False,
                          }

    def __init__(self, dbinfo, do_create=False, do_upgrade=False):

        # Must supply a dbengine if supplying a dbsession
        assert ((not dbinfo.dbengine and not dbinfo.dbsession) or
                (dbinfo.dbengine and dbinfo.dbsession) or
                (dbinfo.dbengine and not dbinfo.dbsession))

        if dbinfo.uri:
            self._db_uri = dbinfo.uri
        else:
            self._db_uri = makeDbUri(dbinfo.db_type, dbinfo.name,
                                     host=dbinfo.host,
                                     port=dbinfo.port, username=dbinfo.username,
                                     password=dbinfo.password)
        if dbinfo.dbengine:
            self._engine = dbinfo.dbengine
        else:
            self._engine = sql.create_engine(self._db_uri,
                                             **self.DEFAULT_ENGINE_ARGS)
            try:
                log.info("Connecting to database '%s'" % self._db_uri)
                self._engine.connect()
            except sql.exc.OperationalError as ex:
                raise ConnectException(str(ex))

        if dbinfo.dbsession:
            self.Session = dbinfo.dbsession
        else:
            # Make the type creating sessions.
            self.Session = sql.orm.sessionmaker(bind=self._engine,
                                                autocommit=True,
                                                autoflush=False)

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

    def dropAll(self):
        log.warn("Dropping all database tables!")

        for dbo_list in [TABLES, ENUMS]:
            tmp = list(dbo_list)
            tmp.reverse()
            for dbo in tmp:
                dbo.drop(bind=self._engine)

    def getArtist(self, session, one=False, **kwargs):
        query = session.query(Artist).filter_by(**kwargs)
        return query.all() if not one else query.one()

    def getMeta(self, session):
        return session.query(Meta).one()

    def deleteOrphans(self, session):
        num_orphaned_artists = 0
        num_orphaned_albums = 0
        num_orphaned_tracks = 0
        found_ids = set()

        # Tracks
        for track in session.query(Track).all():
            if not os.path.exists(track.path):
                log.warn("Deleting track: %s" % str(track))
                session.delete(track)
                num_orphaned_tracks += 1

        session.flush()

        # Artists
        found_ids.clear()
        for artist in session.query(Artist).all():
            if (artist.name == VARIOUS_ARTISTS_NAME or
                    artist.id in found_ids):
                continue

            any_track = session.query(Track).filter(Track.artist_id==artist.id)\
                                            .first()
            if not any_track:
                log.warn("Deleting artist: %s" % str(artist))
                session.delete(artist)
                num_orphaned_artists += 1
            else:
                found_ids.add(artist.id)

        session.flush()

        # Albums
        found_ids.clear()
        for album in session.query(Album).all():
            if album.id in found_ids:
                continue

            any_track = session.query(Track).filter(Track.album_id==album.id)\
                                            .first()
            if not any_track:
                log.warn("Deleting album: %s" % str(album))
                session.delete(album)
                num_orphaned_albums += 1
            else:
                found_ids.add(album.id)

        return (num_orphaned_tracks, num_orphaned_artists, num_orphaned_albums)


def makeDbUri(db_type, name, host=None, port=None,
              username=None, password=None):
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
        elif db_type == "oracle":
            # XXX: Oracle remains untested
            if not (username and password):
                raise ValueError("username and password required")
            # Name is the DSN
            uri = "%s://%s:%s@%s" % (db_type, username, password, name)
        else:
            raise ValueError("Unsupported DB type '%s'. Options are %s" %
                             (str(db_type), str(SUPPORTED_DB_TYPES)))

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
