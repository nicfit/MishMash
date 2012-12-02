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
from __future__ import print_function
import sys, os
import time
import getpass
import logging
from os.path import getmtime, getctime
from datetime import datetime

import eyed3
eyed3.require("0.7")
from eyed3.plugins import Plugin, LoaderPlugin
from eyed3.utils.cli import printError, printMsg, printWarning

import mishmash
mishmash.log.setLevel(logging.INFO)
from mishmash.database import (Database, MissingSchemaException,
                               SUPPORTED_DB_TYPES)
from mishmash.orm import Track, Artist, Album, VARIOUS_ARTISTS_NAME, Meta


class MishMashPlugin(LoaderPlugin):
    NAMES = ['mishmash']
    SUMMARY = u"Music library database."
    DESCRIPTION = u"""
**Requires SQLAlchemy**
"""

    def __init__(self, arg_parser):
        super(MishMashPlugin, self).__init__(arg_parser, cache_files=True)
        self._initCmdLineArgs()

        self._num_added = 0
        self._num_modified = 0

    def _initCmdLineArgs(self):
        g = self.arg_group
        g.add_argument("--create", action="store_true", default=False,
                       dest="do_create",
                       help="Create database schema.")
        g.add_argument("--drop-all", action="store_true", default=False,
                       dest="do_drop",
                       help="Drops all database tables.")

        g.add_argument("--db-type", dest="db_type", default="sqlite",
                       help="Database type. Supported types: %s" %
                            ', '.join(SUPPORTED_DB_TYPES))
        g.add_argument("--database", dest="db_name",
                       default="mishmash.db",
                       help="The name of the datbase (path for sqlite).")
        g.add_argument("--username", dest="username",
                       default=getpass.getuser(),
                       help="Login name for database. Not used for 'sqlite'. "
                            "Default is the user login name.")
        g.add_argument("--password", dest="password", default=None,
                       help="Password for database. Not used for 'sqlite'. ")
        g.add_argument("--host", dest="host", default="localhost",
                       help="Hostname for database. Not used for 'sqlite'. "
                            "The default is 'localhost'")
        g.add_argument("--port", dest="port", default=None,
                       help="Port for database. Not used for 'sqlite'.")

    def start(self, args, config):
        super(MishMashPlugin, self).start(args, config)
        self.start_time = time.time()

        def makeDatabase(do_create):
            return Database(args.db_type, args.db_name,
                            username=args.username, password=args.password,
                            host=args.host, port=args.port,
                            do_create=do_create)

        try:
            self.db = makeDatabase(args.do_create)

            if args.do_drop:
                self.db.dropAllTables()
                printWarning("Database tables dropped")
                if args.do_create:
                    self.db = makeDatabase(True)
                else:
                    sys.exit(0)

        except MissingSchemaException as ex:
            printError("Schema error:")
            printMsg("The table%s '%s' %s missing from the database schema." %
                     ('s' if len(ex.tables) > 1 else '',
                      ", ".join(ex.tables),
                      "are" if len(ex.tables) > 1 else "is"))
            sys.exit(1)

        session = self.db.Session()
        with session.begin():
            # Get the compilation artist, its ID will be used for compilations
            self._comp_artist_id = self.db.getArtist(session,
                                                     name=VARIOUS_ARTISTS_NAME,
                                                     one=True).id

    def handleDirectory(self, d, _):
        audio_files = list(self._file_cache)
        self._file_cache = []

        if not audio_files:
            return

        added_files = []
        modified_files = []

        session = self.db.Session()
        with session.begin():
            for audio_file in audio_files:
                path = audio_file.path

                track = session.query(Track).filter_by(path=path).all()
                if track:
                    track = track[0]
                    if datetime.fromtimestamp(getctime(path)) > track.ctime:
                        modified_files.append(audio_file)
                else:
                    added_files.append(audio_file)

            # Added files
            for audio_file in added_files:
                path = audio_file.path
                info = audio_file.info
                tag = audio_file.tag

                artist_rows = session.query(Artist)\
                                     .filter_by(name=tag.artist).all()
                if artist_rows:
                    if len(artist_rows) > 1:
                        raise NotImplementedError("FIXME")
                    artist = artist_rows[0]
                else:
                    artist = Artist(name=tag.artist)
                    session.add(artist)
                    session.flush()

                album = None
                album_rows = session.query(Album)\
                                    .filter_by(title=tag.album).all()
                if album_rows:
                    if len(album_rows) > 1:
                        raise NotImplementedError("FIXME")
                    album = album_rows[0]
                elif tag.album:
                    album = Album(title=tag.album, artist_id=artist.id)
                    session.add(album)
                    session.flush()

                # Check for a compilation, and update artist_id if necessary
                if album and album.artist_id != artist.id:
                    album.compilation = True
                    album.artist_id = self._comp_artist_id
                    session.add(album)

                track = Track(audio_file=audio_file,
                              album_id=album.id if album else None)
                track.artist_id = artist.id
                session.add(track)
                printWarning("Added file %s" % path)

            # Modified files
            for audio_file in modified_files:
                print("FIXME -- modified: ", audio_file.path)

        self._num_added += len(added_files)
        self._num_modified += len(modified_files)

    def handleDone(self):
        t = time.time() - self.start_time
        print("%d new files" % self._num_added)
        print("%d modified files" % self._num_modified)
        print("%d total files" % self._num_loaded)
        print("%fs time (%f/s)" % (t, self._num_loaded / t))

        session = self.db.Session()
        with session.begin():
            print("\nDatabase:")
            meta = session.query(Meta).one()
            print("Version:", meta.version)
            print("Last Sync:", meta.last_sync)
            meta.last_sync = datetime.now()
            print("%d tracks" % session.query(Track).count())
            print("%d artists" % session.query(Artist).count())
            print("%d albums" % session.query(Album).count())

            for track in session.query(Track).all():
                if not os.path.exists(track.path):
                    print("FIXME -- deleted: ", audio_file.path)
                    raise NotImplementedError("Handle file deletes")



