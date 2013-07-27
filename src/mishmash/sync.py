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
from eyed3.utils.cli import printError, printMsg, printWarning

from .database import Database
from .orm import Track, Artist, Album, VARIOUS_ARTISTS_NAME, Label
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
        for track in session.query(Track).all():
            if not os.path.exists(track.path):
                printWarning("Deleting track %s" % track.path)
                session.delete(track)
                self._num_deleted += 1
        if self._num_deleted:
            session.flush()
        printMsg("All files sync'd")

        # Look for orphans
        num_orphaned_artists = 0
        num_orphaned_albums = 0
        found_ids = set()

        printMsg("Purging orphan artist names...")
        for artist in session.query(Artist).all():
            if (artist.name == VARIOUS_ARTISTS_NAME or
                    artist.id in found_ids):
                continue

            any_track = session.query(Track).filter(Track.artist_id==artist.id)\
                                            .first()
            if not any_track:
                session.delete(artist)
                num_orphaned_artists += 1
            else:
                found_ids.add(artist.id)
        session.flush()

        found_ids.clear()
        printMsg("Purging orphan album names...")
        for album in session.query(Album).all():
            if album.id in found_ids:
                continue

            any_track = session.query(Track).filter(Track.album_id==album.id)\
                                            .first()
            if not any_track:
                session.delete(album)
                num_orphaned_albums += 1
            else:
                found_ids.add(album.id)
        session.flush()

        if self._num_loaded or self._num_deleted:
            print("")
            print("%d files sync'd" % self._num_loaded)
            print("%d tracks added" % self._num_added)
            print("%d tracks modified" % self._num_modified)
            print("%d orphaned tracks deleted" % self._num_deleted)
            print("%d orphaned artists deleted" % num_orphaned_artists)
            print("%d orphaned albums deleted" % num_orphaned_albums)
            print("%fs time (%f/s)" % (t, self._num_loaded / t))
