# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import time
from os.path import getctime
from datetime import datetime

from nicfit import command, getLogger
from sqlalchemy.orm.exc import NoResultFound

import eyed3
import eyed3.main
from eyed3.utils import art
from eyed3.plugins import LoaderPlugin
from eyed3.utils.prompt import PromptExit
from eyed3.main import main as eyed3_main
from eyed3.utils.console import Fore as fg
from eyed3.core import TXXX_ALBUM_TYPE, VARIOUS_TYPE, LP_TYPE, SINGLE_TYPE

import inotify.adapters

from ..orm import (Track, Artist, Album, Tag, Meta, Image, Library,
                   VARIOUS_ARTISTS_ID, MAIN_LIB_NAME)
from .. import console
from ..core import Command
from .._console import pout, perr
from ..library import MusicLibrary

log = getLogger(__name__)


IMAGE_TYPES = {"artist": (Image.LOGO_TYPE, Image.ARTIST_TYPE, Image.LIVE_TYPE),
               "album": (Image.FRONT_COVER_TYPE, Image.BACK_COVER_TYPE,
                         Image.MISC_COVER_TYPE),
              }


class SyncPlugin(LoaderPlugin):
    """An eyeD3 file scanner/loader plugin."""

    NAMES = ['mishmash-sync']
    SUMMARY = u"Synchronize files/directories with a Mishmash database."
    DESCRIPTION = u""

    def __init__(self, arg_parser):
        super().__init__(arg_parser, cache_files=True, track_images=True)

        eyed3.main.setFileScannerOpts(
            arg_parser, paths_metavar="PATH_OR_LIB",
            paths_help="Files/directory paths, or individual music libraries. "
                       "No arguments will sync all configured libraries.")

        arg_parser.add_argument(
                "--monitor", action="store_true", dest="monitor",
                help="Monitor sync'd dirs for changes.")
        arg_parser.add_argument(
                "-f", "--force", action="store_true", dest="force",
                help="Force sync a library when sync=False.")
        arg_parser.add_argument(
                "--no-purge", action="store_true", dest="no_purge",
                help="Do not purge orphaned data (tracks, artists, albums, "
                     "etc.). This will make for a faster sync, and useful when "
                     "files were only added to a library.")
        arg_parser.add_argument(
                "--no-prompt", action="store_true", dest="no_prompt",
                help="Skip files that require user input.")

        self._inotify = None
        self._synced_dirs = []

    def start(self, args, config):
        import eyed3.utils.prompt

        self._num_loaded = 0
        self._num_added = 0
        self._num_modified = 0
        self._num_deleted = 0
        self._db_session = None

        eyed3.utils.prompt.DISABLE_PROMPT = "raise" if args.no_prompt else None

        super().start(args, config)
        self.start_time = time.time()
        self._db_session = args.db_session

        try:
            lib = self._db_session.query(Library)\
                                  .filter_by(name=args._library.name).one()
        except NoResultFound:
            lib = Library(name=args._library.name)
            self._db_session.add(lib)
            self._db_session.flush()
        self._lib_name = lib.name
        self._lib_id = lib.id

        if self.args.monitor:
            self._inotify = inotify.adapters.Inotify()

    def _getArtist(self, session, name, resolved_artist):
        artist_rows = session.query(Artist).filter_by(name=name,
                                                      lib_id=self._lib_id).all()
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
                        pout(fg.yellow("Updating artist") + ": " + name)
                    resolved_artist = artist
            else:
                # Artist match
                artist = artist_rows[0]
        else:
            # New artist
            artist = Artist(name=name, lib_id=self._lib_id)
            session.add(artist)
            session.flush()
            pout(fg.green("Adding artist") + ": " + name)

        return artist, resolved_artist

    def _syncAudioFile(self, audio_file, album_type, d_datetime, session):
        path = audio_file.path
        info = audio_file.info
        tag = audio_file.tag

        album = None
        is_various = (album_type == VARIOUS_TYPE)

        if not info or not tag:
            log.warn("File missing %s, skipping: %s" %
                     ("audio" if not info else "tag/metadata", path))
            return
        elif None in (tag.title, tag.artist):
            log.warn("File missing required artist and/or title "
                     "metadata, skipping: %s" % path)
            return

        # Used when a duplicate artist is resolved for the entire directory.
        resolved_artist = None
        resolved_album_artist = None

        try:
            track = session.query(Track)\
                           .filter_by(path=path, lib_id=self._lib_id).one()
        except NoResultFound:
            track = None
        else:
            if datetime.fromtimestamp(getctime(path)) == track.ctime:
                # Track is in DB and the file is not modified.
                # stash the album though, we'll look for artwork
                # updates later
                album = track.album
                return

        # Either adding the track (track == None)
        # or modifying (track != None)

        artist, resolved_artist = self._getArtist(session, tag.artist,
                                                  resolved_artist)
        if tag.album_type != SINGLE_TYPE:
            if tag.album_artist and tag.artist != tag.album_artist:
                album_artist, resolved_album_artist = \
                        self._getArtist(session, tag.album_artist,
                                        resolved_album_artist)
            else:
                album_artist = artist

            if artist is None:
                # see PromptExit
                return

            album_artist_id = album_artist.id if not is_various \
                                              else VARIOUS_ARTISTS_ID
            album_rows = session.query(Album)\
                                .filter_by(title=tag.album,
                                           lib_id=self._lib_id,
                                           artist_id=album_artist_id).all()
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
                pout(fg.yellow("Updating album") + ": " + album.title)
            elif tag.album:
                album = Album(title=tag.album, lib_id=self._lib_id,
                              artist_id=album_artist_id, type=album_type,
                              release_date=rel_date,
                              original_release_date=or_date,
                              recording_date=rec_date,
                              date_added=d_datetime)
                session.add(album)
                pout(fg.green("Adding album") + ": " + album.title)

            session.flush()

        if not track:
            track = Track(audio_file=audio_file, lib_id=self._lib_id)
            self._num_added += 1
            pout(fg.green("Adding track") + ": " + path)
        else:
            track.update(audio_file)
            self._num_modified += 1
            pout(fg.yellow("Updating track") + ": " + path)

        genre = tag.genre
        genre_tag = None
        if genre:
            try:
                genre_tag = session.query(Tag)\
                                   .filter_by(name=genre.name,
                                              lib_id=self._lib_id).one()
            except NoResultFound:
                genre_tag = Tag(name=genre.name, lib_id=self._lib_id)
                session.add(genre_tag)
                session.flush()

        track.artist_id = artist.id
        track.album_id = album.id if album else None
        if genre_tag:
            track.tags.append(genre_tag)
        session.add(track)

        if album:
            # Tag images
            for img in tag.images:
                for img_type in art.TO_ID3_ART_TYPES:
                    if img.picture_type in \
                            art.TO_ID3_ART_TYPES[img_type]:
                        break
                    img_type = None

                if img_type is None:
                    log.warn("Skipping unsupported image type: %s" %
                             img.picture_type)
                    continue

                new_img = Image.fromTagFrame(img, img_type)
                if new_img:
                    syncImage(new_img,
                              album if img_type in IMAGE_TYPES["album"]
                                    else album.artist,
                              session)
                else:
                    log.warn("Invalid image in tag")

        return album

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

        album = None
        session = self._db_session
        for audio_file in audio_files:
            album = self._syncAudioFile(audio_file, album_type, d_datetime,
                                        session)

        if album:
            # Directory images.
            for img_file in image_files:
                img_type = art.matchArtFile(img_file)
                if img_type is None:
                    log.warn("Skipping unrecognized image file: %s" %
                              img_file)
                    continue

                new_img = Image.fromFile(img_file, img_type)
                if new_img:
                    new_img.description = os.path.basename(img_file)
                    syncImage(new_img, album if img_type in IMAGE_TYPES["album"]
                                             else album.artist,
                              session)
                else:
                    log.warn("Invalid image file: " + img_file)

        if self.args.monitor:
            self._watchDir(d)

    def _watchDir(self, d):
        d = d.encode(eyed3.LOCAL_FS_ENCODING)
        self._synced_dirs.append(d)
        self._inotify.add_watch(d)

    def handleDone(self):
        t = time.time() - self.start_time
        session = self._db_session

        session.query(Meta).one().last_sync = datetime.now()

        num_orphaned_artists = 0
        num_orphaned_albums = 0
        if not self.args.no_purge:
            log.debug("Purging orphans (tracks, artists, albums) from database")
            (self._num_deleted,
             num_orphaned_artists,
             num_orphaned_albums) = deleteOrphans(session)

        if self._num_loaded or self._num_deleted:
            pout("")
            pout("== Library '{}' sync'd [ {:f}s time ({:f} files/s) ] =="
                .format(self._lib_name, t, self._num_loaded / t))
            pout("%d files sync'd" % self._num_loaded)
            pout("%d tracks added" % self._num_added)
            pout("%d tracks modified" % self._num_modified)
            if not self.args.no_purge:
                pout("%d orphaned tracks deleted" % self._num_deleted)
                pout("%d orphaned artists deleted" % num_orphaned_artists)
                pout("%d orphaned albums deleted" % num_orphaned_albums)
            pout("")

    def monitor(self):
        log.info("Monitor {:d} directories for file changes"
                 .format(len(self._synced_dirs)))
        for event in self._inotify.event_gen():
            if event is None:
                continue
            (header, type_names, watch_path, filename) = event
            log.debug("WD=({:d}) MASK=({:d}) COOKIE=({:d}) LEN=({:d}) "
                      "MASK->NAMES={:s} WATCH-PATH=[{:s}] FILENAME=[{:s}]"
                      .format(header.wd, header.mask, header.cookie, header.len,
                              type_names,
                              watch_path.decode(eyed3.LOCAL_FS_ENCODING),
                              filename.decode(eyed3.LOCAL_FS_ENCODING)))

    def unmonitor(self):
        for d in self._synced_dirs:
            self._inotify.remove_watch(d)

def deleteOrphans(session):
    num_orphaned_artists = 0
    num_orphaned_albums = 0
    num_orphaned_tracks = 0
    found_ids = set()

    # Tracks
    for track in session.query(Track).all():
        if not os.path.exists(track.path):
            pout(fg.red("Removing track") + ": " + track.path)
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
        any_album = session.query(Album).filter(Album.artist_id == artist.id) \
                                        .first()
        if not any_track and not any_album:
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
    def _img_str(i):
        return "%s - %s" % (i.type, i.description)

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
                pout(fg.green("Updating image") + ": " + _img_str(img))
            img = None
            break

    if img:
        # Add image
        current.images.append(img)
        session.add(current)
        pout(fg.green("Adding image") + ": " + _img_str(img))


@command.register
class Sync(Command):
    NAME = "sync"
    HELP = "Syncronize music directories with database."

    def __init__(self, subparsers):
        super(Sync, self).__init__(subparsers)
        self.plugin = SyncPlugin(self.parser)
        self.args = None

    def _run(self, args=None):
        args = args or self.args
        args.plugin = self.plugin

        # TODO: add CommandException to get rid of return 1 etc at this level

        libs = {lib.name: lib for lib in args.config.music_libs}
        if not libs and not args.paths:
            perr("\nMissing at least one path/library in which to sync!\n")
            self.parser.print_usage()
            return 1

        sync_libs = []
        if args.paths:
            file_paths = []
            for arg in args.paths:
                if arg in libs:
                    # Library name
                    sync_libs.append(libs[arg])
                else:
                    # Path
                    file_paths.append(arg)
            if file_paths:
                sync_libs.append(MusicLibrary(MAIN_LIB_NAME, paths=file_paths))
        else:
            sync_libs = list(libs.values())

        args.db_engine, args.db_session = self.db_engine, self.db_session
        try:
            for lib in sync_libs:
                if not lib.sync and not args.force:
                    pout("[{}] - sync=False".format(lib.name), log=log)
                    continue
                args._library = lib
                args.paths = lib.paths
                pout("{}yncing library '{}': paths={}"
                     .format("Force s" if args.force else "S", lib.name,
                             lib.paths), log=log)
                r = eyed3_main(args, None)
                if r != 0:
                    return r
        except IOError as err:
            perr(str(err))
            return 1

        self.db_session.commit()
        if args.monitor:
            # FIXME: kick monitor off in a sep process.
            try:
                self.plugin.monitor()
            finally:
                self.plugin.unmonitor()
