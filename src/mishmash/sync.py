# -*- coding: utf-8 -*-
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
from __future__ import print_function

import os
import sys
import time
import logging
from os.path import getmtime, getctime
from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound

from eyed3.plugins import LoaderPlugin
from eyed3.utils.console import printError, printMsg, printWarning

from .database import Database
from .orm import Track, Artist, Album, VARIOUS_ARTISTS_NAME, Label, Meta
from .log import log


class SyncPlugin(LoaderPlugin):
    NAMES = ['mishmash-sync']
    SUMMARY = u"Synchronize files/direcotries with a Mishmash database."
    DESCRIPTION = u""

    def __init__(self, arg_parser):
        super(SyncPlugin, self).__init__(arg_parser, cache_files=True)

        self._num_added = 0
        self._num_modified = 0
        self._num_deleted = 0
        self._comp_artist_id = None
        self.db = None

    def start(self, args, config):
        super(SyncPlugin, self).start(args, config)
        self.start_time = time.time()
        self.db = args.db

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

                if not tag:
                    log.warn("File missing tag/metadata, skipping: %s" % path)
                    continue
                elif None in (tag.title, tag.artist):
                    log.warn("File missing required artist and/or title "
                             "metadata, skipping: %s" % path)
                    continue

                track = session.query(Track).filter_by(path=path).all()
                if track:
                    track = track[0]
                    if datetime.fromtimestamp(getctime(path)) <= track.ctime:
                        # track is in DB and the file is not modified
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
                rel_date = tag.release_date
                rec_date = tag.recording_date
                or_date = tag.original_release_date

                # Helper for getting the stringified date or None
                def _procDate(d):
                    return str(d) if d else None

                if album_rows:
                    if len(album_rows) > 1:
                        raise NotImplementedError("FIXME")
                    album = album_rows[0]

                    album.compilation = is_comp

                    album.release_date = _procDate(rel_date)
                    album.original_release_date = _procDate(or_date)
                    album.recording_date = _procDate(rec_date)
                elif tag.album:
                    album = Album(title=tag.album, artist_id=album_artist_id,
                                  compilation=is_comp,
                                  release_date=_procDate(rel_date),
                                  original_release_date=_procDate(or_date),
                                  recording_date=_procDate(rec_date))
                    session.add(album)

                session.flush()

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

        printMsg("All files sync'd")
        with session.begin():
            self.db.getMeta(session).last_sync = datetime.now()

            num_orphaned_artists = 0
            num_orphaned_albums = 0
            if not self.args.no_purge:
                printMsg("Purging orphans (tracks, artists, albums) from "
                         "database...")
                (self._num_deleted,
                 num_orphaned_artists,
                 num_orphaned_albums) = self.db.deleteOrphans(session)

        if self._num_loaded or self._num_deleted:
            print("")
            print("%d files sync'd" % self._num_loaded)
            print("%d tracks added" % self._num_added)
            print("%d tracks modified" % self._num_modified)
            print("%d orphaned tracks deleted" % self._num_deleted)
            print("%d orphaned artists deleted" % num_orphaned_artists)
            print("%d orphaned albums deleted" % num_orphaned_albums)
            print("%fs time (%f/s)" % (t, self._num_loaded / t))
