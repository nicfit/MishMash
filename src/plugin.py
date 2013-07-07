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
import os
import sys
import time
import getpass
import logging
from os.path import getmtime, getctime
from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func

import eyed3
eyed3.require("0.7")
from eyed3 import LOCAL_ENCODING as ENCODING
from eyed3.plugins import LoaderPlugin
from eyed3.utils.cli import printError, printMsg, printWarning

import mishmash
mishmash.log.setLevel(logging.INFO)
from mishmash.database import (Database, MissingSchemaException,
                               SUPPORTED_DB_TYPES)
from mishmash.orm import Track, Artist, Album, VARIOUS_ARTISTS_NAME, Meta, Label


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
        self._num_deleted = 0

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
        g.add_argument("--port", dest="port", default=5432,
                       help="Port for database. Not used for 'sqlite'.")

        g.add_argument("-s", "--search", dest="search", action="store",
                       type=unicode, metavar="STRING",
                       help="Search all tables for STRING.")
        g.add_argument("--artists", dest="show_artists", action="store_true",
                       help="Output all artists in a formatted and sorted "
                            "list.")
        g.add_argument("--random", dest="random", action="store", type=int,
                       default=None, metavar="N",
                       help="Output N random tracks (by path).")

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

        # This directory of files can be
        # 1) an album by a single artist (tag.artist and tag.album all equal)
        # 2) a comp (tag.album equal, tag.artist differ)
        # 3) not associated with a collection (tag.artist and tag.album differ)
        artists = set([f.tag.artist for f in audio_files if f.tag])
        albums = set([f.tag.album for f in audio_files if f.tag])
        is_album = len(artists) == 1 and len(albums) == 1
        is_comp = len(artists) > 1 and len(albums) == 1

        session = self.db.Session()
        with session.begin():
            for audio_file in audio_files:
                path = audio_file.path
                info = audio_file.info
                tag = audio_file.tag

                track = session.query(Track).filter_by(path=path).all()
                if track:
                    track = track[0]
                    if datetime.fromtimestamp(getctime(path)) <= track.ctime:
                        # Have the track and the file is not modified
                        continue

                # Either adding the track (track == None)
                # or modifying (track != None)

                artist_rows = self.db.getArtist(session, name=tag.artist)
                if artist_rows:
                    if len(artist_rows) > 1:
                        raise NotImplementedError("FIXME")
                    artist = artist_rows[0]
                else:
                    artist = Artist(name=tag.artist)
                    session.add(artist)
                    session.flush()

                album_artist_id = artist.id if not is_comp \
                    else self._comp_artist_id
                album = None
                album_rows = session.query(Album)\
                                    .filter_by(title=tag.album,
                                               artist_id=album_artist_id).all()
                if album_rows:
                    if len(album_rows) > 1:
                        raise NotImplementedError("FIXME")
                    album = album_rows[0]
                elif tag.album:
                    # FIXME: really, the dates need to be separate
                    release_date = tag.best_release_date
                    album = Album(title=tag.album, artist_id=album_artist_id,
                                  compilation=is_comp,
                                  release_date=str(release_date)
                                  if release_date else None)
                    session.add(album)
                    session.flush()

                # FIXME: Handle upates to release date

                if not track:
                    track = Track(audio_file=audio_file)
                    self._num_added += 1
                    printWarning("Adding file %s" % path)
                else:
                    track.update(audio_file)
                    self._num_modified += 1
                    printWarning("Updating file %s" % path)

                genre = tag.genre
                label = None
                if genre:
                    try:
                        label = \
                            session.query(
                                Label).filter_by(name=genre.name).one()
                    except NoResultFound:
                        label = Label(name=genre.name)
                        session.add(label)
                        session.flush()

                track.artist_id = artist.id
                track.album_id = album.id if album else None
                if label:
                    track.labels.append(label)
                session.add(track)

    def handleDone(self):
        t = time.time() - self.start_time

        session = self.db.Session()

        if self.args.show_artists:
            banner = None
            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                if banner != artist.sort_name[0]:
                    banner = artist.sort_name[0]
                    printMsg(u"\n== %s ==" % banner)
                printMsg(u"\t%s" % artist.sort_name)

        elif self.args.search:
            print("\nSearch:")
            s = self.args.search

            print("Artists:")
            for artist in session.query(Artist).filter(
                    Artist.name.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d)" % (artist.name, artist.id))

            print("Albums:")
            for album in session.query(Album).filter(
                    Album.title.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d) (artist: %s)" % (album.title, album.id,
                                                       album.artist.name))

            print("Tracks:")
            for track in session.query(Track).filter(
                    Track.title.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d) (artist: %s) (album: %s)" %
                      (track.title, track.id,
                       track.artist.name,
                       track.album.title if track.album else None))
        elif self.args.random:
            for track in session.query(Track)\
                                .order_by(func.random())\
                                .limit(self.args.random).all():
                print(track.path)
        else:
            with session.begin():
                print("\nDatabase:")
                meta = session.query(Meta).one()
                print("Version:", meta.version)
                print("Last Sync:", meta.last_sync)
                meta.last_sync = datetime.now()
                print("%d tracks" % session.query(Track).count())
                print("%d artists" % session.query(Artist).count())
                print("%d albums" % session.query(Album).count())
                print("%d labels" % session.query(Label).count())

                for track in session.query(Track).all():
                    if not os.path.exists(track.path):
                        printWarning("Deleting track %s" % track.path)
                        session.delete(track)
                    self._num_deleted += 1

        if self._num_loaded:
            print("")
            print("%d new files" % self._num_added)
            print("%d modified files" % self._num_modified)
            print("%d deleted files" % self._num_deleted)
            print("%d total files" % self._num_loaded)
            print("%fs time (%f/s)" % (t, self._num_loaded / t))
