# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2013-2014  Travis Shirk <travis@pobox.com>
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
import time
from os.path import getctime
from datetime import datetime
from fnmatch import fnmatch

from sqlalchemy.orm.exc import NoResultFound

from eyed3.id3.frames import ImageFrame
from eyed3.plugins import LoaderPlugin
from eyed3.utils.console import printMsg
from eyed3.utils.console import Fore as fg
from eyed3.utils.prompt import PromptExit
from eyed3.core import TXXX_ALBUM_TYPE, VARIOUS_TYPE, LP_TYPE, SINGLE_TYPE

from .orm import (Track, Artist, Album, Label, Meta, Image,
                  VARIOUS_ARTISTS_ID)
from .log import log
from . import console


FILE_IMG_TYPE_MAP = {
        Image.FRONT_COVER_TYPE: ["cover-front", "cover-alternate*", "cover",
                                 "folder", "front", "cover*-*front", "flier"],
        Image.BACK_COVER_TYPE: ["cover-back", "cover*-*back"],
        Image.MISC_COVER_TYPE: ["cover-insert*", "cover-liner*", "cover-disc",
                                "cover-media*"],
        Image.LOGO_TYPE: ["logo"],
        Image.ARTIST_TYPE: ["artist*"],
}
'''Maps the orm Image ``type`` to a list of filenames for that type.'''

TAG_IMG_TYPE_MAP = {
        Image.FRONT_COVER_TYPE: [ImageFrame.FRONT_COVER, ImageFrame.OTHER,
                                 ImageFrame.ICON, ImageFrame.LEAFLET],
        Image.BACK_COVER_TYPE: [ImageFrame.BACK_COVER],
        Image.MISC_COVER_TYPE: [ImageFrame.MEDIA],
        Image.LOGO_TYPE: [ImageFrame.BAND_LOGO],
        Image.ARTIST_TYPE: [ImageFrame.LEAD_ARTIST, ImageFrame.ARTIST,
                            ImageFrame.BAND],
        Image.LIVE_TYPE: [ImageFrame.DURING_PERFORMANCE,
                          ImageFrame.DURING_RECORDING]
}
'''Maps the orm Image ``type`` to a list of ID3 image (APIC) picture types.'''

# ID3 image types not mapped above:
#    OTHER_ICON          = 0x02
#    CONDUCTOR           = 0x09
#    COMPOSER            = 0x0B
#    LYRICIST            = 0x0C
#    RECORDING_LOCATION  = 0x0D
#    VIDEO               = 0x10
#    BRIGHT_COLORED_FISH = 0x11
#    ILLUSTRATION        = 0x12
#    PUBLISHER_LOGO      = 0x14

IMAGE_TYPES = {"artist": (Image.LOGO_TYPE, Image.ARTIST_TYPE, Image.LIVE_TYPE),
               "album": (Image.FRONT_COVER_TYPE, Image.BACK_COVER_TYPE,
                         Image.MISC_COVER_TYPE),
              }


class SyncPlugin(LoaderPlugin):
    NAMES = ['mishmash-sync']
    SUMMARY = u"Synchronize files/directories with a Mishmash database."
    DESCRIPTION = u""

    def __init__(self, arg_parser):
        super(SyncPlugin, self).__init__(arg_parser, cache_files=True,
                                         track_images=True)

        self.arg_group.add_argument(
                "--no-prompt", action="store_true", dest="no_prompt",
                help="Skip files that require user input.")

        self._num_added = 0
        self._num_modified = 0
        self._num_deleted = 0
        self.DBSession = None

    def start(self, args, config):
        import eyed3.utils.prompt
        eyed3.utils.prompt.DISABLE_PROMPT = "raise" if args.no_prompt else None

        super(SyncPlugin, self).start(args, config)
        self.start_time = time.time()
        self.DBSession = args.db_session

    def _getArtist(self, session, name, resolved_artist):
        artist_rows = session.query(Artist).filter_by(name=name).all()
        if artist_rows:
            if len(artist_rows) > 1 and resolved_artist:
                # Use previously resolved artist for this directory.
                artist = resolved_artist
            elif len(artist_rows) > 1:
                # Resolve artist
                try:
                    heading = "Multiple artists names '%s'" % \
                              artist_rows[0].name
                    artist = console.selectArtist(fg.blue(heading),
                                                  choices=artist_rows,
                                                  allow_create=True)
                except PromptExit:
                    log.warn("Duplicate artist requires user "
                             "intervention to resolve.")
                    artist = None
                else:
                    if artist not in artist_rows:
                        session.add(artist)
                        session.flush()
                    resolved_artist = artist
            else:
                # Artist match
                artist = artist_rows[0]
        else:
            # New artist
            artist = Artist(name=name)
            session.add(artist)
            session.flush()

        return artist, resolved_artist

    def handleDirectory(self, d, _):
        audio_files = list(self._file_cache)
        self._file_cache = []

        image_files = self._dir_images
        self._dir_images = []

        if not audio_files:
            return

        d_datetime = datetime.fromtimestamp(getctime(d))

        # This directory of files can be:
        # 1) an album by a single artist (tag.artist, or tag.albun_srtist and
        #    tag.album all equal)
        # 2) a comp (tag.album equal, tag.artist differ)
        # 3) not associated with a collection (tag.artist and tag.album differ)
        artists = set([f.tag.artist for f in audio_files if f.tag])
        album_artists = set([f.tag.album_artist for f in audio_files if f.tag])
        albums = set([f.tag.album for f in audio_files if f.tag])
        for s in artists, album_artists, albums:
            if None in s:
                s.remove(None)

        is_various = (len(artists) > 1 and len(album_artists) == 0 and
                      len(albums) == 1)

        def type_hint():
            hints = set()
            for tag in [f.tag for f in audio_files if f.tag]:
                hint_frame = tag.user_text_frames.get(TXXX_ALBUM_TYPE)
                if hint_frame:
                    hints.add(hint_frame.text)
            if len(hints) > 1:
                log.warn("Inconsistent type hints: %s" % str(hints))
                return None
            else:
                return hints.pop() if hints else None

        album_type = type_hint() or LP_TYPE
        if is_various and album_type not in (None, VARIOUS_TYPE):
            # is_various overrides
            log.warn("Using type various despite files saying %s" % album_type)
        album_type = VARIOUS_TYPE if is_various else album_type

        # Used when a duplicate artist is resolved for the entire directory.
        resolved_artist = None
        resolved_album_artist = None

        session = self.DBSession()
        with session.begin():
            for audio_file in audio_files:
                path = audio_file.path
                info = audio_file.info
                tag = audio_file.tag

                if not info or not tag:
                    log.warn("File missing %s, skipping: %s" %
                             ("audio" if not info else "tag/metadata", path))
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

                artist, resolved_artist = self._getArtist(session, tag.artist,
                                                          resolved_artist)
                album = None

                if tag.album_type != SINGLE_TYPE:
                    if tag.album_artist and tag.artist != tag.album_artist:
                        album_artist, resolved_album_artist = \
                                self._getArtist(session, tag.album_artist,
                                                resolved_album_artist)
                    else:
                        album_artist = artist

                    if artist is None:
                        # see PromptExit
                        continue

                    album_artist_id = album_artist.id if not is_various \
                                                      else VARIOUS_ARTISTS_ID
                    album_rows = session.query(Album)\
                                        .filter_by(title=tag.album,
                                                   artist_id=album_artist_id)\
                                        .all()
                    rel_date = tag.release_date
                    rec_date = tag.recording_date
                    or_date = tag.original_release_date

                    if album_rows:
                        if len(album_rows) > 1:
                            # This artist has more than one album with the same
                            # title.
                            raise NotImplementedError("FIXME")
                        album = album_rows[0]

                        album.type = album_type
                        album.release_date = rel_date
                        album.original_release_date = or_date
                        album.recording_date = rec_date
                    elif tag.album:
                        album = Album(title=tag.album,
                                      artist_id=album_artist_id,
                                      type=album_type,
                                      release_date=rel_date,
                                      original_release_date=or_date,
                                      recording_date=rec_date,
                                      date_added=d_datetime)
                        session.add(album)

                    session.flush()

                if not track:
                    track = Track(audio_file=audio_file)
                    self._num_added += 1
                    print(fg.green("Adding track") + ": " + path)
                else:
                    track.update(audio_file)
                    self._num_modified += 1
                    print(fg.yellow("Updating track") + ": " + path)

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

                if album:
                    # Tag images
                    for img in tag.images:
                        for img_type in TAG_IMG_TYPE_MAP:
                            if img.picture_type in TAG_IMG_TYPE_MAP[img_type]:
                                break
                            img_type = None

                        if img_type is None:
                            log.warn("Skipping unsupported image type: %s" %
                                     img.picture_type)
                            continue

                        new_img = Image.fromTagFrame(img, img_type)
                        syncImage(new_img,
                                  album if img_type in IMAGE_TYPES["album"]
                                        else album.artist,
                                  session)

            if album:
                # Directory images.
                for img_file in image_files:
                    basename, ext = os.path.splitext(os.path.basename(img_file))
                    for img_type in FILE_IMG_TYPE_MAP:
                        if True in [fnmatch(basename.lower(), fname)
                                    for fname in FILE_IMG_TYPE_MAP[img_type]]:
                            break
                        img_type = None

                    if img_type is None:
                        log.warn("Skipping unrecognized image file: %s" %
                                  img_file)
                        continue

                    new_img = Image.fromFile(img_file, img_type)
                    new_img.description = basename + ext
                    syncImage(new_img, album if img_type in IMAGE_TYPES["album"]
                                             else album.artist,
                              session)

    def handleDone(self):
        t = time.time() - self.start_time
        session = self.DBSession()

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
            print(fg.red("Removing track") + ": " + track.path)
            session.delete(track)
            num_orphaned_tracks += 1
            log.warn("Deleting track: %s" % str(track))

    session.flush()

    # Artists
    found_ids.clear()
    for artist in session.query(Artist).all():
        if (artist.id == VARIOUS_ARTISTS_ID or
                artist.id in found_ids):
            continue

        any_track = session.query(Track).filter(Track.artist_id == artist.id) \
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

        any_track = session.query(Track).filter(Track.album_id == album.id) \
                                        .first()
        if not any_track:
            log.warn("Deleting album: %s" % str(album))
            session.delete(album)
            num_orphaned_albums += 1
        else:
            found_ids.add(album.id)

    return (num_orphaned_tracks, num_orphaned_artists, num_orphaned_albums)


def syncImage(img, current, session):
    '''Add or updated the Image.'''

    for db_img in current.images:

        img_info = (img.type, img.md5, img.size)
        db_img_info = (db_img.type, db_img.md5, db_img.size)

        if db_img_info == img_info:
            img = None
            break
        elif (db_img.type == img.type and
                db_img.description == img.description):

            if img.md5 != db_img.md5:
                # Update image
                current.images.remove(db_img)
                current.images.append(img)
                session.add(current)
            img = None
            break

    if img:
        # Add image
        current.images.append(img)
        session.add(current)
