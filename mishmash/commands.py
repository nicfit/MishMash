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
from argparse import Namespace

import eyed3

import eyed3.main
from eyed3.main import main as eyed3_main
from eyed3.utils import ArgumentParser
from eyed3.utils.console import printMsg, Style
from eyed3.utils.console import Fore as fg, Back as bg
from eyed3.utils.prompt import prompt
from eyed3.core import VARIOUS_TYPE

from . import database
from .console import promptArtist, selectArtist

from .orm import Track, Artist, Album, Meta, Label
from .log import log
from .util import normalizeCountry, mostCommon, commonDirectoryPrefix


_cmds = []


class Command(object):
    cmds = {}

    def __init__(self, name, help, subparsers=None):
        self.subparsers = subparsers
        self.parser = self.subparsers.add_parser(name, help=help)
        self.parser.set_defaults(func=self.run)
        Command.cmds[name] = self

    def run(self, args):
        self.args = args
        self.db_engine, self.db_session = database.init(self.args.db_uri)
        return self._run()

    def _run(self):
        raise Exception("Must implement the run() function")

    @staticmethod
    def initAll(subparsers):
        for cmd in _cmds:
            cmd(subparsers)


# init subcommand
class Init(Command):
    def __init__(self, subparsers=None):
        super(Init, self).__init__("init", "Initialize music database.",
                                   subparsers)
        self.parser.add_argument("--drop-all", action="store_true",
                                 help="Drop all tables and re-init")

    def _run(self):
        missing_tables = []

        engine, session = self.db_engine, self.db_session
        try:
            database.check(engine)
        except database.MissingSchemaException as ex:
            missing_tables = ex.tables

        dropped = False
        if self.args.drop_all:
            printMsg("Dropping schema...")
            database.dropAll(engine)
            dropped = True

        if missing_tables or dropped:
            printMsg("Creating schema...")
            database.create(session, None if dropped else missing_tables)

        printMsg("Initialized")


# sync subcommand
class Sync(Command):
    def __init__(self, subparsers=None):
        super(Sync, self).__init__("sync", "Syncronize music and database.",
                                   subparsers)
        self.parser.add_argument(
                "--no-purge", action="store_true", dest="no_purge",
                help="Do not purge orphaned data (tracks, artists, albums, "
                     "etc.). This will make for a faster sync, and useful when "
                     "files were only added to a library.")

        from . import sync
        self.parser = eyed3.main.makeCmdLineParser(self.parser)
        self.plugin = sync.SyncPlugin(self.parser)
        self.args = None

    def _run(self, paths=[], config=None, backup=False, excludes=None,
             fs_encoding=eyed3.LOCAL_FS_ENCODING, quiet=False, no_purge=False):

        if self.args:
            args = self.args
        else:
            # Running as an API, make an args object with the right info
            args = Namespace()
            args.paths = paths
            args.config = config
            args.backup = backup
            args.excludes = excludes
            args.fs_encoding = fs_encoding
            args.quiet = quiet
            args.list_plugins = False
            args.no_purge = no_purge

        args.plugin = self.plugin
        args.db_engine, args.db_session = self.db_engine, self.db_session

        return eyed3_main(args, None)


# info subcommand
class Info(Command):
    def __init__(self, subparsers=None):
        super(Info, self).__init__(
            "info", "Show information about music database.", subparsers)

    def _run(self):
        session = self.db_session

        printMsg("\nDatabase:")
        printMsg("\tURI: %s" % self.args.db_uri)
        meta = session.query(Meta).one()
        printMsg("\tVersion: %s" % meta.version)
        printMsg("\tLast Sync: %s" % meta.last_sync)

        printMsg("\nMusic:")
        printMsg("\t%d tracks" % session.query(Track).count())
        printMsg("\t%d artists" % session.query(Artist).count())
        printMsg("\t%d albums" % session.query(Album).count())
        printMsg("\t%d labels" % session.query(Label).count())


# random subcommand
class Random(Command):
    def __init__(self, subparsers=None):
        super(Random, self).__init__("random", "Retrieve random tracks.",
                                     subparsers)
        self.parser.add_argument("count", type=int, metavar="COUNT")

    def _run(self):
        from sqlalchemy.sql.expression import func

        session = self.db_session

        for track in session.query(Track).order_by(func.random())\
                                         .limit(self.args.count).all():
            printMsg(track.path)


class Search(Command):
    def __init__(self, subparsers=None):
        super(Search, self).__init__("search", "Search music database.",
                                     subparsers)
        self.parser.add_argument("search_pattern", type=unicode,
                                 metavar="SEARCH", help="Search string.")

    def _run(self):
        session = self.db_session

        s = self.args.search_pattern
        printMsg("\nSearching for '%s'" % s)

        results = database.search(session, s)

        printMsg("Artists:")
        for artist in results["artists"]:
            printMsg(u"\t%s (id: %d)" % (artist.name, artist.id))

        printMsg("Albums:")
        for album in results["albums"]:
            printMsg(u"\t%s (id: %d) (artist: %s)" % (album.title, album.id,
                                                      album.artist.name))

        printMsg("Tracks:")
        for track in results["tracks"]:
            printMsg(u"\t%s (id: %d) (artist: %s) (album: %s)" %
                     (track.title, track.id,
                      track.artist.name,
                      track.album.title if track.album else None))


class List(Command):
    def __init__(self, subparsers=None):
        super(List, self).__init__("list", "Listings from music database.",
                                   subparsers)
        list_choices = ("artists", "albums")
        self.parser.add_argument(
            "what", metavar="WHAT", choices=list_choices,
            help="What to list. Valid values are %s." %
                 ','.join(["'%s'" % c for c in list_choices]))

    def _run(self):
        session = self.db_session

        if self.args.what == "artists":
            banner = None

            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                if banner != artist.sort_name[0]:
                    banner = artist.sort_name[0]
                    printMsg(u"\n== %s ==" % banner)
                printMsg(u"\t%s" % artist.sort_name)
        elif self.args.what == "albums":
            def albumSortKey(alb):
                return alb.release_date

            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                printMsg(artist.sort_name)

                albums = sorted(artist.albums, key=albumSortKey)
                for alb in albums:
                    printMsg(u"\t%s (released: %s)" % (alb.title,
                                                       alb.release_date))
        else:
            # This should not happen if ArgumentParser is doing its job
            assert(not "unsupported list value")


class Relocate(Command):
    def __init__(self, subparsers=None):
        super(Relocate, self).__init__(
            "relocate", "Relocate file paths from one root prefix to another",
            subparsers)
        self.parser.add_argument("oldroot", help="The path to replace.")
        self.parser.add_argument("newroot", help="The substitute path.")

    def _run(self):
        session = self.db_session

        oldroot, newroot = self.args.oldroot, self.args.newroot

        if oldroot[-1] != os.sep:
            oldroot += os.sep
        if newroot[-1] != os.sep:
            newroot += os.sep

        num_relocates = 0
        with session.begin():

            for track in session.query(Track).filter(
                    Track.path.like(u"%s%%" % oldroot)).all():
                track.path = track.path.replace(oldroot, newroot)
                num_relocates += 1

            session.flush()
        printMsg("%d files relocated from '%s' to '%s'" %
                 (num_relocates, oldroot, newroot))


class SplitArtists(Command):
    def __init__(self, subparsers=None):
        super(SplitArtists, self).__init__(
                "split-artists",
                "Split a single artist name into N distinct artists.",
                subparsers)
        self.parser.add_argument("artist", type=unicode,
                                 help="The name of the artist.")

    def _displayArtistMusic(self, artist, albums, singles):
        if albums:
            printMsg(u"%d albums by %s:" % (len(albums),
                                            Style.bright(fg.blue(artist.name))))
            for alb in albums:
                printMsg(u"%s %s" % (str(alb.getBestDate()).center(17),
                                     alb.title))

        if singles:
            printMsg(u"%d single tracks by %s" %
                     (len(singles), Style.bright(fg.blue(artist.name))))
            for s in singles:
                printMsg(u"\t%s" % (s.title))

    def _run(self):
        session = self.db_session

        artists = session.query(Artist)\
                         .filter(Artist.name == self.args.artist).all()
        if not artists:
            printMsg(u"Artist not found: %s" % self.args.artist)
            return 1
        elif len(artists) > 1:
            artist = selectArtist(fg.blue("Select which '%s' to split...") %
                                  artists[0].name,
                                  choices=artists, allow_create=False)
        else:
            artist = artists[0]

        # Albums by artist
        albums = list(artist.albums) + artist.getAlbumsByType(VARIOUS_TYPE)
        # Singles by artist and compilations the artist appears on
        singles = artist.getTrackSingles()

        if len(albums) < 2 and len(singles) < 2:
            print("%d albums and %d singles found for '%s', nothing to do." %
                    (len(albums), len(singles), artist.name))
            return 0

        self._displayArtistMusic(artist, albums, singles)

        def _validN(_n):
            return _n > 1 and _n <= len(albums)
        n = prompt("\nEnter the number of distinct artists", type_=int,
                   validate=_validN)
        new_artists = []
        with session.begin():
            for i in range(1, n + 1):
                printMsg(Style.bright(u"\n%s #%d") % (fg.blue(artist.name), i))

                # Reuse original artist for first
                a = artist if i == 1 else Artist(name=artist.name,
                                                 date_added=artist.date_added)
                a.origin_city = prompt("   City", required=False)
                a.origin_state = prompt("   State", required=False)
                a.origin_country = prompt("   Country", required=False,
                                          type_=normalizeCountry)

                new_artists.append(a)

            if not Artist.checkUnique(new_artists):
                print(fg.red("Artists must be unique."))
                return 1

            for a in new_artists:
                session.add(a)

            # New Artist objects need IDs
            session.flush()

            printMsg(Style.bright("\nAssign albums to the correct artist."))
            for i, a in enumerate(new_artists):
                printMsg("Enter %s%d%s for %s from %s%s%s" %
                         (Style.BRIGHT, i + 1, Style.RESET_BRIGHT,
                          a.name,
                          Style.BRIGHT, a.origin(country_code="iso3c",
                                                 title_case=False),
                          Style.RESET_BRIGHT))

            # prompt for correct artists
            def _promptForArtist(_text):
                a = prompt(_text, type_=int,
                           choices=range(1, len(new_artists) + 1))
                return new_artists[a - 1]

            print("")
            for alb in albums:
                # Get some of the path to help the decision
                path = commonDirectoryPrefix(*[t.path for t in alb.tracks])
                path = os.path.join(*path.split(os.sep)[-2:])

                a = _promptForArtist("%s (%s)" % (alb.title, path))
                if alb.type != "various":
                    alb.artist_id = a.id
                for track in alb.tracks:
                    if track.artist_id == artist.id:
                        track.artist_id = a.id

            print("")
            for track in singles:
                a = _promptForArtist(track.title)
                track.artist_id = a.id

            session.flush()


class MergeArtists(Command):
    def __init__(self, subparsers=None):
        super(MergeArtists, self).__init__(
                "merge-artists",
                "Merge two or more artists into a single artist.",
                subparsers)
        self.parser.add_argument(
                "artists", type=unicode, nargs="+",
                help="The artist names to merge.")

    def _run(self):
        session = self.db_session

        merge_list = []
        for artist_arg in self.args.artists:
            artists = session.query(Artist)\
                             .filter(Artist.name == artist_arg).all()
            if len(artists) == 1:
                merge_list.append(artists[0])
            elif len(artists) > 1:
                merge_list += selectArtist(
                        fg.blue("Select the artists to merge..."),
                        multiselect=True, choices=artists)

        if len(merge_list) > 1:
            # Reuse lowest id
            artist_ids = {a.id: a for a in merge_list}
            min_id = min(*artist_ids.keys())
            artist = artist_ids[min_id]

            mc = mostCommon
            new_artist = promptArtist(
                    "Merging %d artists into new artist..." % len(merge_list),
                    default_name=mc([a.name for a in merge_list]),
                    default_city=mc([a.origin_city for a in merge_list]),
                    default_state=mc([a.origin_state for a in merge_list]),
                    default_country=mc([a.origin_country for a in merge_list]),
                    artist=artist)
        else:
            print("Nothing to do, %s" %
                    ("artist not found" if not len(merge_list)
                                        else "only one artist found"))
            return 1

        with session.begin():
            assert(new_artist in merge_list)
            session.flush()

            for artist in merge_list:
                if artist is new_artist:
                    continue

                for alb in list(artist.albums):
                    if alb.type != "various":
                        alb.artist_id = new_artist.id
                        artist.albums.remove(alb)
                        new_artist.albums.append(alb)

                    for track in alb.tracks:
                        if track.artist_id == artist.id:
                            # gotta check in case alb is type various
                            track.artist_id = new_artist.id

                for track in artist.getTrackSingles():
                    track.artist_id = new_artist.id

                # flush to get new artist ids in sync before delete, otherwise
                # cascade happens.
                session.flush()
                session.delete(artist)

            session.flush()

        # FIXME: promt for whether the tags should be updated with the new
        # name if it is new.


_cmds.extend([Init, Sync, Info, Random, Search, List, Relocate,
              SplitArtists, MergeArtists])


def makeCmdLineParser():
    from . import __version_txt__ as VERSION_MSG
    from os.path import expandvars

    parser = ArgumentParser(prog="mishmash", version=VERSION_MSG,
                            main_logger="mishmash")

    db_group = parser.add_argument_group(title="Database settings and options")

    default_uri = os.environ.get("MISHMASH_DB",
                                 expandvars("sqlite:///$HOME/mishmash.db"))
    db_group.add_argument("-D", "--database", dest="db_uri", metavar="url",
            default=default_uri,
            help="Database URL. The default is '%s'" % default_uri)

    subparsers = parser.add_subparsers(
            title="Sub commands",
            description="Database command line options are required by most "
                        "sub commands.")

    # help subcommand; turns it into the less intuitive --help format.
    def _help(args):
        if args.command:
            parser.parse_args([args.command, "--help"])
        else:
            parser.print_help()
        parser.exit(0)
    help_parser = subparsers.add_parser("help", help="Show help.")
    help_parser.set_defaults(func=_help)
    help_parser.add_argument("command", nargs='?', default=None)

    Command.initAll(subparsers)

    return parser
