import os
import platform
import time
import collections
from pathlib import Path
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
from eyed3.core import (TXXX_ALBUM_TYPE, VARIOUS_TYPE, LP_TYPE, SINGLE_TYPE,
                        EP_TYPE)
from nicfit.console.ansi import Fg
from nicfit.console import pout, perr

from ...orm import (Track, Artist, Album, Meta, Image, Library,
                    VARIOUS_ARTISTS_ID, MAIN_LIB_NAME)
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
    SUMMARY = u"Synchronize files/directories with a Mishmash database."
    DESCRIPTION = u""

    def __init__(self, arg_parser):
        """Constructor"""
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

        self.monitor_proc = None

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
        self._lib = lib

        if self.args.monitor:
            from ._inotify import Monitor, SYNC_INTERVAL
            if self.monitor_proc is None:
                self.monitor_proc = Monitor()
            # Monitor roots, file dir are watched as the files are traversed
            for p in self.args.paths:
                self._watchDir(p)

    def _getArtist(self, session, name, resolved_artist):
        artist_rows = session.query(Artist).filter_by(name=name,
                                                      lib_id=self._lib.id).all()
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
                    log.warn("Duplicate artist requires user "
                             "intervention to resolve.")
                    artist = None
                else:
                    if artist not in artist_rows:
                        session.add(artist)
                        session.flush()
                        pout(Fg.blue("Updating artist") + ": " + name)
                    resolved_artist = artist
            else:
                # Artist match
                artist = artist_rows[0]
        else:
            # New artist
            artist = Artist(name=name, lib_id=self._lib.id)
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
                           .filter_by(path=path, lib_id=self._lib.id).one()
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
                                           lib_id=self._lib.id,
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
                pout(Fg.yellow("Updating album") + ": " + album.title)
            elif tag.album:
                album = Album(title=tag.album, lib_id=self._lib.id,
                              artist_id=album_artist_id, type=album_type,
                              release_date=rel_date,
                              original_release_date=or_date,
                              recording_date=rec_date,
                              date_added=d_datetime)
                session.add(album)
                pout(Fg.green("Adding album") + ": " + album.title)

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

    def _albumTypeHint(self, audio_files):
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
            artists = set()
            album_artists = set()
            albums = set()
            for tag in [tag for f in audio_files if f.tag]:
                if tag.artist:
                    artists.add(tag.artist)
                if tag.album_artist:
                    album_artists.add(tag.album_artist)
                if tag.album:
                    albums.add(tag.album)

            is_various = (len(artists) > 1 and len(album_artists) == 0 and
                          len(albums) == 1)
            if is_various:
                return VARIOUS_TYPE
            else:
                return EP_TYPE if len(audio_files) < EP_MAX_SIZE_HINT \
                               else LP_TYPE

        if len(types) > 1:
            log.warn("Inconsistent type hints: %s" % str(types.keys()))
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
                album = self._syncAudioFile(audio_file, album_type, d_datetime,
                                            session)
            except Exception as ex:
                # TODO: log and skip????
                raise

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


@command.register
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

            pout("{}yncing library '{}': paths={}"
                 .format("Force s" if args.force else "S", lib.name, lib.paths),
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


"""
Test:
    * touch a music file: IN_OPEN, IN_ATTRIB, IN_CLOSE_WRITE
    * touch a non-music file: IN_OPEN, IN_ATTRIB, IN_CLOSE_WRITE
    * touch a music dir
    - touch a non-music dir
    * chmod/chown a music file
    * chmod/chown a non-music file
    * chmod/chown a music dir
    * chmod/chown a non-music dir
    * edit a file
    * add a file
    * rm a file
    - add a music dir
    - rm a music dir
    - add a non-music dir
    - rm a non-music dir
    - rm cover art
    - add cover art
Problems:
    - A change of a non-music dir (e.g. root music dir files, images) is not
      synced since it is not in a lib dir
    - rm a music dir::

        Syncing b"./music/complete/(1988) Demo '88" (lib: Music)
        Syncing library 'Music': paths={b"./music/complete/(1988) Demo '88"}
        <mishmash:MainThread> [ERROR]: file not found: ./music/complete/(1988) Demo '88
        Traceback (most recent call last):
          File "/home/travis/devel/mishmash/mishmash/__main__.py", line 48, in main
            retval = args.command_func(args, args.config) or 0
          File "/home/travis/devel/mishmash/mishmash/core.py", line 17, in run
            retval = super().run(args)
          File "/home/travis/.virtualenvs/mishmash/lib/python3.6/site-packages/nicfit/command.py", line 38, in run
            return self._run()
          File "/home/travis/devel/mishmash/mishmash/commands/sync.py", line 540, in _run
            result = _syncLib(MusicLibrary(lib, paths=paths))
          File "/home/travis/devel/mishmash/mishmash/commands/sync.py", line 509, in _syncLib
            return eyed3_main(args, None)
          File "/home/travis/.virtualenvs/mishmash/lib/python3.6/site-packages/eyed3/main.py", line 50, in main
            fs_encoding=args.fs_encoding)
          File "/home/travis/.virtualenvs/mishmash/lib/python3.6/site-packages/eyed3/utils/__init__.py", line 72, in walk
            raise IOError("file not found: %s" % path)
        OSError: file not found: ./music/complete/(1988) Demo '88
        OSError: file not found: ./music/complete/(1988) Demo '88
""" # noqa
