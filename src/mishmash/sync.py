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

from eyed3.id3.frames import ImageFrame
from eyed3.plugins import LoaderPlugin
from eyed3.utils import guessMimetype
from eyed3.utils.console import printError, printMsg, printWarning

from .orm import (Track, Artist, Album, VARIOUS_ARTISTS_NAME, Label, Meta,
                  Image)
from . import orm
from .log import log


ARTWORK_FILENAMES = {orm.FRONT_COVER_TYPE: ["cover-front", "cover", "folder"],
                     orm.BACK_COVER_TYPE: ["cover-back"],
                    }
TAG_IMAGE_TYPES_TO_DB_IMG_TYPES = {
        ImageFrame.FRONT_COVER: orm.FRONT_COVER_TYPE,
        ImageFrame.BACK_COVER: orm.BACK_COVER_TYPE,
}


class SyncPlugin(LoaderPlugin):
    NAMES = ['mishmash-sync']
    SUMMARY = u"Synchronize files/directories with a Mishmash database."
    DESCRIPTION = u""

    def __init__(self, arg_parser):
        super(SyncPlugin, self).__init__(arg_parser, cache_files=True)

        self._num_added = 0
        self._num_modified = 0
        self._num_deleted = 0
        self._comp_artist_id = None
        self.DBSession = None
        self._dir_images = []

    def start(self, args, config):
        super(SyncPlugin, self).start(args, config)
        self.start_time = time.time()
        self.DBSession = args.db_session

        session = self.DBSession()
        with session.begin():
            # Get the compilation artist, its ID will be used for compilations
            self._comp_artist_id = session.query(Artist)\
                                          .filter_by(name=VARIOUS_ARTISTS_NAME)\
                                          .one().id

    def handleFile(self, f, *args, **kwargs):
        super(SyncPlugin, self).handleFile(f, *args, **kwargs)

        if self.audio_file is None:
            mt = guessMimetype(f)
            if mt and mt.startswith("image/"):
                self._dir_images.append(f)

    def handleDirectory(self, d, _):
        audio_files = list(self._file_cache)
        self._file_cache = []

        image_files = self._dir_images
        self._dir_images = []

        if not audio_files:
            return

        # This directory of files can be:
        # 1) an album by a single artist (tag.artist and tag.album all equal)
        # 2) a comp (tag.album equal, tag.artist differ)
        # 3) not associated with a collection (tag.artist and tag.album differ)
        artists = set([f.tag.artist for f in audio_files if f.tag])
        albums = set([f.tag.album for f in audio_files if f.tag])
        is_album = len(artists) == 1 and len(albums) == 1
        is_comp = len(artists) > 1 and len(albums) == 1

        session = self.DBSession()
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

                try:
                    track = session.query(Track).filter_by(path=path).one()
                except NoResultFound:
                    track = None
                else:
                    if datetime.fromtimestamp(getctime(path)) == track.ctime:
                        # Track is in DB and the file is not modified.
                        # stash the album though, we'll look for artwork
                        # updates later
                        album = track.album
                        continue

                # Either adding the track (track == None)
                # or modifying (track != None)

                artist_rows = session.query(Artist).filter_by(name=tag.artist)\
                                                   .all()
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

                if album_rows:
                    if len(album_rows) > 1:
                        raise NotImplementedError("FIXME")
                    album = album_rows[0]

                    album.compilation = is_comp

                    album.release_date = rel_date
                    album.original_release_date = or_date
                    album.recording_date = rec_date
                elif tag.album:
                    album = Album(title=tag.album, artist_id=album_artist_id,
                                  compilation=is_comp,
                                  release_date=rel_date,
                                  original_release_date=or_date,
                                  recording_date=rec_date)
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

                # Tag images
                for img in tag.images:
                    if not img.picture_type in TAG_IMAGE_TYPES_TO_DB_IMG_TYPES:
                        log.warn("Skipping tag image of type: %d" %
                                 img.picture_type)
                        continue

                    img_type = TAG_IMAGE_TYPES_TO_DB_IMG_TYPES[img.picture_type]
                    add_image = True
                    for db_image in album.images:
                        if (db_image.type == img_type and
                                db_image.description == img.description):
                            # FIXME: md5 check to not add the same front a ton
                            # Update
                            # TODO
                            add_image = False
                            break

                    if add_image:
                        # TODO
                        pass

            for img_file in image_files:
                basename = os.path.splitext(os.path.basename(img_file))[0]
                for img_type in ARTWORK_FILENAMES:
                    if basename in ARTWORK_FILENAMES[img_type]:
                        break
                    img_type = None

                if img_type is None:
                    log.warn("Skipping unrecognized image file: %s" % img_file)
                    continue

                log.debug("Album image: %s %s" % (img_type, img_file))

                add_image = True
                album_images = [img for img in album.images
                                if img.type == img_type]
                for img in album_images:
                    if img.description == basename:
                        add_image = False
                        ctime = datetime.fromtimestamp(getctime(img_file))
                        size = os.stat(img_file).st_size
                        if (ctime != img.ctime) or (size != img.size):
                            # Update
                            img.update(img_file)
                            session.add(img)
                        break

                if not album_images or add_image:
                    printWarning("Adding image file %s" % img_file)

                    db_image = Image.fromFile(img_file)
                    db_image.type = img_type
                    db_image.description = basename

                    album.images.append(db_image)
                    session.add(album)

    def handleDone(self):
        t = time.time() - self.start_time
        session = self.DBSession()

        printMsg("All files sync'd")
        with session.begin():
            session.query(Meta).one().last_sync = datetime.now()

            num_orphaned_artists = 0
            num_orphaned_albums = 0
            if not self.args.no_purge:
                printMsg("Purging orphans (tracks, artists, albums) from "
                         "database...")
                (self._num_deleted,
                 num_orphaned_artists,
                 num_orphaned_albums) = deleteOrphans(session)

        if self._num_loaded or self._num_deleted:
            printMsg("")
            printMsg("%d files sync'd" % self._num_loaded)
            printMsg("%d tracks added" % self._num_added)
            printMsg("%d tracks modified" % self._num_modified)
            printMsg("%d orphaned tracks deleted" % self._num_deleted)
            printMsg("%d orphaned artists deleted" % num_orphaned_artists)
            printMsg("%d orphaned albums deleted" % num_orphaned_albums)
            printMsg("%fs time (%f/s)" % (t, self._num_loaded / t))


def deleteOrphans(session):
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
