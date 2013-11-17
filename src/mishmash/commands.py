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
import getpass
from argparse import Namespace

import eyed3

import eyed3.main
from eyed3.main import main as eyed3_main
from eyed3.utils import ArgumentParser
from eyed3.utils.console import printMsg, Style
from eyed3.utils.prompt import prompt
from eyed3.core import VARIOUS_TYPE

from . import database

from .orm import Track, Artist, Album, Meta, Label
from .log import log
from .util import normalizeCountry


_cmds = []

def _bold(s):
    return Style.BRIGHT + s + Style.RESET_BRIGHT

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

    def _run(self):
        session = self.db_session

        artists = session.query(Artist)\
                         .filter(Artist.name == self.args.artist).all()
        if not artists:
            printMsg(u"Artist not found: %s" % self.args.artist)
            return 1
        elif len(artists) > 1:
            # User needs to choose which artist to split on.
            raise NotImplementedError("FIXME")
        else:
            artist = artists[0]

        # Albums by artist
        albums = list(artist.albums) + artist.getAlbumsByType(VARIOUS_TYPE)
        if len(albums) < 2:
            # Does not appear to be a multiple artist scenario
            raise NotImplementedError("FIXME")

        if albums:
            printMsg(u"Found the following albums by %s" % _bold(artist.name))
            for alb in albums:
                printMsg(u"%s %s" % (str(alb.getBestDate()).center(17),
                                     alb.title))

        # Track singles by artist
        singles = artist.getTrackSingles()

        if singles:
            printMsg(u"And the following single tracks by %s" %
                     _bold(artist.name))
            for s in singles:
                printMsg(u"\t%s" % (s.title))

        n = prompt("\nNumber of distinct artists", type_=int)
        new_artists = []
        with session.begin():
            for i in range(1, n + 1):
                printMsg(_bold(u"\n%s #%d") % (artist.name, i))

                # Reuse original artist for first
                a = artist if i == 1 else Artist(name=artist.name,
                                                 date_added=artist.date_added)
                a.origin_city = prompt("Origin city", required=False)
                a.origin_state = prompt("Origin state", required=False)
                a.origin_country = prompt("Origin country", required=False,
                                          type_=normalizeCountry)

                new_artists.append(a)
                session.add(a)

            printMsg(_bold("\nAssign albums to the correct artist."))
            for i, artist in enumerate(new_artists):
                printMsg("Enter %d for %s from %s" %
                         (i, artist.name, artist.origin))
            # FIXME: need to be careful to set only the right bits for
            # type=various
            print("")
            album_map = {}
            for alb in albums:
                a = prompt(alb.title, type_=int,
                           choices=range(len(new_artists)))
                a = new_artists[a]

                if a not in album_map:
                    album_map[a] = []
                album_map[a].append(alb)

            for artist in album_map:
                # FIXME: reflect the origins in all tags
                for alb in album_map[artist]:
                    alb.artist_id = artist.id
                    for trk in alb.tracks:
                        trk.artist_id = artist.id
                # FIXME: process singles tracks that need to be updated

            raise ValueError("remove me, testing rollback")
            # Add new artists, flush changed values.
            for artist in new_artists:
                if artist.id is None:
                    session.add(artist)
            session.flush()


_cmds.extend([Init, Sync, Info, Random, Search, List, Relocate, SplitArtists])


def makeCmdLineParser():
    from .info import VERSION_MSG
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
