import os
import platform
import time
import collections
from pathlib import Path
from os.path import getctime
from datetime import datetime

from nicfit import getLogger
from sqlalchemy.orm.exc import NoResultFound

import eyed3
import eyed3.main
from eyed3.utils import art
from eyed3.plugins import LoaderPlugin
from eyed3.utils.prompt import PromptExit
from eyed3.main import main as eyed3_main
from eyed3.core import TXXX_ALBUM_TYPE, VARIOUS_TYPE, LP_TYPE, SINGLE_TYPE, EP_TYPE
from nicfit.console.ansi import Fg
from nicfit.console import pout, perr

from ...util import normalizeCountry
from ...orm import (Track, Artist, Album, Meta, Image, Library,
                    VARIOUS_ARTISTS_ID, VARIOUS_ARTISTS_NAME, MAIN_LIB_NAME, NULL_LIB_ID)
from ... import console
from ... import database as db
from ...core import Command, EP_MAX_SIZE_HINT
from ...config import MusicLibrary

from .utils import syncImage, deleteOrphans

log = getLogger(__name__)
IMAGE_TYPES = {"artist": (Image.LOGO_TYPE, Image.ARTIST_TYPE, Image.LIVE_TYPE),
               "album": (Image.FRONT_COVER_TYPE, Image.BACK_COVER_TYPE,
                         Image.MISC_COVER_TYPE),
              }


class SyncPlugin(LoaderPlugin):
    """An eyeD3 file scanner/loader plugin."""

    NAMES = ['mishmash-sync']
    SUMMARY = "Synchronize files/directories with a Mishmash database."
    DESCRIPTION = ""

    def __init__(self, arg_parser):
        """Constructor"""
        super().__init__(arg_parser, cache_files=True, track_images=True)

        eyed3.main.setFileScannerOpts(
            arg_parser, default_recursive=True, paths_metavar="PATH_OR_LIB",
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
        arg_parser.add_argument(
            "--speed", default="fast", choices=("fast", "normal"),
            help="Sync speed. 'fast' will skips files whose timestamps have not changed, while "
                 "'normal' scans all files all the time.")

        self.monitor_proc = None
        self._num_added = 0
        self._num_modified = 0
        self._num_deleted = 0
        self._db_session = None
        self._lib = None
        self.start_time = None

    def start(self, args, config):
        import eyed3.utils.prompt

        self._num_loaded = 0

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
        self._lib = lib

        if self.args.monitor:
            from ._inotify import Monitor
            if self.monitor_proc is None:
                self.monitor_proc = Monitor()
            # Monitor roots, file dir are watched as the files are traversed
            for p in self.args.paths:
                self._watchDir(p)

    def _getArtist(self, session, name, origin, resolved_artist):
        origin_dict = {"origin_city": origin.city if origin else None,
                       "origin_state": origin.state if origin else None,
                       "origin_country": normalizeCountry(origin.country) if origin else None,
                      }
        if name == VARIOUS_ARTISTS_NAME:
            artist_rows = [session.query(Artist).filter_by(name=VARIOUS_ARTISTS_NAME,
                                                           lib_id=NULL_LIB_ID).one()]
        else:
            artist_rows = session.query(Artist)\
                                 .filter_by(name=name,
                                            lib_id=self._lib.id,
                                            **origin_dict)\
                                 .all()

        if artist_rows:
            if len(artist_rows) > 1 and resolved_artist:
                # Use previously resolved artist for this directory.
                artist = resolved_artist
            elif len(artist_rows) > 1:
                # Resolve artist
                try:
                    heading = "Multiple artists names '%s'" % \
                              artist_rows[0].name
                    artist = console.selectArtist(Fg.blue(heading),
                                                  choices=artist_rows,
                                                  allow_create=True)
                except PromptExit:
                    log.warning("Duplicate artist requires user intervention to resolve.")
                    artist = None
                else:
                    if artist not in artist_rows:
                        session.add(artist)
                        session.flush()
                        pout(Fg.blue("Updating artist") + ": " + name)
                    resolved_artist = artist
            else:
                assert len(artist_rows) == 1
                # Artist match
                artist = artist_rows[0]
        else:
            # New artist
            artist = Artist(name=name, lib_id=self._lib.id, **origin_dict)
            session.add(artist)
            session.flush()
            pout(Fg.green("Adding artist") + ": " + name)

        return artist, resolved_artist

    def _syncAudioFile(self, audio_file, album_type, d_datetime, session):
        path = audio_file.path
        info = audio_file.info
        tag = audio_file.tag

        album = None
        is_various = (album_type == VARIOUS_TYPE)

        if not info or not tag:
            log.warning(f"File missing {'audio' if not info else 'tag/metadata'}, skipping: {path}")
            return None, None
        elif None in (tag.title, tag.artist):
            log.warning("File missing required artist and/or title "
                        "metadata, skipping: %s" % path)
            return None, None

        # Used when a duplicate artist is resolved for the entire directory.
        resolved_artist = None
        resolved_album_artist = None

        try:
            track = session.query(Track)\
                           .filter_by(path=path, lib_id=self._lib.id).one()
        except NoResultFound:
            track = None
        else:
            if (self.args.speed == "fast"
                    and datetime.fromtimestamp(getctime(path)) == track.ctime):
                # Track is in DB and the file is not modified.
                return track, track.album

        # Either adding the track (track == None)
        # or modifying (track != None)

        artist, resolved_artist = self._getArtist(session, tag.artist, tag.artist_origin,
                                                  resolved_artist)
        if album_type != SINGLE_TYPE:
            if tag.album_artist and tag.artist != tag.album_artist:
                album_artist, resolved_album_artist = self._getArtist(session, tag.album_artist,
                                                                      tag.artist_origin,
                                                                      resolved_album_artist)
            else:
                album_artist = artist

            if artist is None:
                # see PromptExit
                return None, None

            album_artist_id = album_artist.id if not is_various \
                                              else VARIOUS_ARTISTS_ID
            rel_date = tag.release_date
            rec_date = tag.recording_date
            or_date = tag.original_release_date

            # Original release date
            if or_date:
                album = session.query(Album).filter_by(lib_id=self._lib.id,
                                                       artist_id=album_artist_id,
                                                       title=tag.album,
                                                       original_release_date=or_date).one_or_none()
            # Release date
            if not album and rel_date:
                album = session.query(Album).filter_by(lib_id=self._lib.id,
                                                       artist_id=album_artist_id,
                                                       title=tag.album,
                                                       release_date=rel_date).one_or_none()
            # Recording date
            if not album and rec_date:
                album = session.query(Album).filter_by(lib_id=self._lib.id,
                                                       artist_id=album_artist_id,
                                                       title=tag.album,
                                                       release_date=rel_date,
                                                       recording_date=rec_date).one_or_none()
            if album is None:
                album = Album(title=tag.album, lib_id=self._lib.id,
                              artist_id=album_artist_id, type=album_type,
                              release_date=rel_date,
                              original_release_date=or_date,
                              recording_date=rec_date,
                              date_added=d_datetime)
                pout(f"{Fg.green('Adding album')}: {album.title}")
                session.add(album)
            else:
                if album.type != album_type:
                    pout(Fg.yellow("Updating album") + ": " + album.title)
                    album.type = album_type

            session.flush()

        if not track:
            track = Track(audio_file=audio_file, lib_id=self._lib.id)
            self._num_added += 1
            pout(Fg.green("Adding track") + ": " + path)
        else:
            track.update(audio_file)
            self._num_modified += 1
            pout(Fg.yellow("Updating track") + ": " + path)

        track.artist_id = artist.id
        track.album_id = album.id if album else None

        if tag.genre:
            # Not uncommon for multiple genres to be 0x00 delimited
            for genre in tag.genre.name.split("\x00"):
                genre_tag = db.getTag(genre, session, self._lib.id, add=True)
                track.tags.append(genre_tag)

        session.add(track)

        if album:
            # Tag images
            img_type = None
            for img in tag.images:
                for img_type in art.TO_ID3_ART_TYPES:
                    if img.picture_type in art.TO_ID3_ART_TYPES[img_type]:
                        break
                    img_type = None

                if img_type is None:
                    log.warning(f"Skipping unsupported image type: {img.picture_type}")
                    continue

                new_img = Image.fromTagFrame(img, img_type)
                if new_img:
                    syncImage(new_img,
                              album if img_type in IMAGE_TYPES["album"]
                                    else album.artist,
                              session)
                else:
                    log.warning("Invalid image in tag")

        return track, album

    @staticmethod
    def _albumTypeHint(audio_files):
        types = collections.Counter()

        # This directory of files can be:
        # 1) an album by a single artist (tag.artist, or tag.album_artist and
        #    tag.album all equal)
        # 2) a comp (tag.album equal, tag.artist differ)
        # 3) not associated with a collection (tag.artist and tag.album differ)

        for tag in [f.tag for f in audio_files if f.tag]:
            album_type = tag.user_text_frames.get(TXXX_ALBUM_TYPE)
            if album_type:
                types[album_type.text] += 1

        if len(types) == 1:
            return types.most_common()[0][0]

        if len(types) == 0:
            artist_set = set()
            album_artist_set = set()
            albums = list()
            for tag in [f.tag for f in audio_files if f.tag]:
                if tag.artist:
                    artist_set.add(tag.artist)

                if tag.album_artist:
                    album_artist_set.add(tag.album_artist)

                if tag.album:
                    albums.append(tag.album)

            is_various = (
                len(artist_set) > 1
                and (len(album_artist_set) == 0 or album_artist_set == {VARIOUS_ARTISTS_NAME})
                and len(albums) == len(audio_files)
            )

            if is_various:
                return VARIOUS_TYPE
            elif len(albums) == len(audio_files):
                return LP_TYPE if len(audio_files) > EP_MAX_SIZE_HINT else EP_TYPE
            else:
                return SINGLE_TYPE

        if len(types) > 1:
            log.warning("Inconsistent type hints: %s" % str(types.keys()))
            return None

    def handleDirectory(self, d, _):
        pout(Fg.blue("Syncing directory") + ": " + str(d))
        audio_files = list(self._file_cache)
        self._file_cache = []

        image_files = self._dir_images
        self._dir_images = []

        if not audio_files:
            return

        d_datetime = datetime.fromtimestamp(getctime(d))

        album_type = self._albumTypeHint(audio_files) or LP_TYPE

        album = None
        session = self._db_session
        for audio_file in audio_files:
            try:
                track, album = self._syncAudioFile(audio_file, album_type, d_datetime, session)
            except Exception as ex:
                log.error(f"{audio_file.path} sync error: {ex}")
                # Continue

        if album:
            # Directory images.
            for img_file in image_files:
                img_type = art.matchArtFile(img_file)
                if img_type is None:
                    log.warning(f"Skipping unrecognized image file: {img_file}")
                    continue

                new_img = Image.fromFile(img_file, img_type)
                if new_img:
                    new_img.description = os.path.basename(img_file)
                    syncImage(new_img, album if img_type in IMAGE_TYPES["album"]
                                             else album.artist,
                              session)
                else:
                    log.warning(f"Invalid image file: {img_file}")

        session.commit()
        if self.args.monitor:
            self._watchDir(d)

    def _watchDir(self, d):
        valid_path = False
        dirpath = Path(d)
        for root in [Path(p) for p in self.args.paths]:
            try:
                dirpath.relative_to(root)
            except ValueError:
                continue
            else:
                valid_path = True
                self.monitor_proc.dir_queue.put((self._lib.name, dirpath))
                # Add parents up to root. It is safe to all the same dir to
                # the  Monitor
                parent = dirpath.parent
                try:
                    parent.relative_to(root)
                except ValueError:
                    # Added a root
                    pass
                else:
                    while parent != root:
                        self.monitor_proc.dir_queue.put((self._lib.name,
                                                         parent))
                        parent = parent.parent
                break
        assert valid_path

    def handleDone(self):
        t = time.time() - self.start_time
        session = self._db_session

        session.query(Meta).one().last_sync = datetime.utcnow()
        self._lib.last_sync = datetime.utcnow()

        num_orphaned_artists = 0
        num_orphaned_albums = 0
        if not self.args.no_purge:
            log.debug("Purging orphans (tracks, artists, albums) from database")
            (self._num_deleted,
             num_orphaned_artists,
             num_orphaned_albums) = deleteOrphans(session)

        if self._num_loaded or self._num_deleted:
            pout("")
            pout("== Library '{}' sync'd [ {:.2f}s time ({:.1f} files/sec) ] =="
                .format(self._lib.name, t, self._num_loaded / t))
            pout("%d files sync'd" % self._num_loaded)
            pout("%d tracks added" % self._num_added)
            pout("%d tracks modified" % self._num_modified)
            if not self.args.no_purge:
                pout("%d orphaned tracks deleted" % self._num_deleted)
                pout("%d orphaned artists deleted" % num_orphaned_artists)
                pout("%d orphaned albums deleted" % num_orphaned_albums)
            pout("")


@Command.register
class Sync(Command):
    NAME = "sync"
    HELP = "Synchronize music directories with database."

    def __init__(self, subparsers):
        super(Sync, self).__init__(subparsers)
        self.plugin = SyncPlugin(self.parser)
        self.args = None

    def _run(self, args=None):
        args = args or self.args
        args.plugin = self.plugin

        if args.monitor and platform.system() == "Darwin":
            perr("Monitor mode is not supported on OS/X\n")
            self.parser.print_usage()
            return 1

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

        def _syncLib(lib):
            args._library = lib

            args.paths = []
            for p in lib.paths:
                args.paths.append(str(p) if isinstance(p, Path) else p)

            pout("{}yncing library '{}': paths={}".format("Force s" if args.force else "S",
                                                          lib.name, lib.paths),
                 log=log)

            args.excludes = lib.excludes
            return eyed3_main(args, None)

        try:
            for lib in sync_libs:
                if not lib.sync and not args.force:
                    pout("[{}] - sync=False".format(lib.name), log=log)
                    continue
                result = _syncLib(lib)
                if result != 0:
                    return result
        except IOError as err:
            perr(str(err))
            return 1

        if args.monitor:
            from ._inotify import SYNC_INTERVAL
            monitor = self.plugin.monitor_proc

            # Commit now, since we won't be returning
            self.db_session.commit()

            monitor.start()
            try:
                while True:
                    if monitor.sync_queue.empty():
                        time.sleep(SYNC_INTERVAL / 2)
                        continue

                    sync_libs = {}
                    for i in range(monitor.sync_queue.qsize()):
                        lib, path = monitor.sync_queue.get_nowait()
                        if lib not in sync_libs:
                            sync_libs[lib] = set()
                        sync_libs[lib].add(path)

                    for lib, paths in sync_libs.items():
                        result = _syncLib(MusicLibrary(lib, paths=paths))
                        if result != 0:
                            return result
                        self.db_session.commit()
            finally:
                monitor.join()
