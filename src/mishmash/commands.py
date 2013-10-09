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
from eyed3.utils.console import printError, printMsg, printWarning

from .database import (SUPPORTED_DB_TYPES, DBInfo, Database,
                       MissingSchemaException)
from .orm import Track, Artist, Album, Meta, Label
from .log import log


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
        self.dbinfo = DBInfo(args.db_type, args.db_name,
                             username=args.username, password=args.password,
                             host=args.host, port=args.port)
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
        try:
            db = Database(self.dbinfo, do_create=False)
        except MissingSchemaException as ex:
            db = None

        dropped = False
        if db and self.args.drop_all:
            printWarning("Dropping all database tables.")
            db.dropAll()
            dropped = True

        if not db or dropped:
            printMsg("Initializing...")
            db = Database(self.dbinfo, do_create=True)


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
        db = Database(self.dbinfo)
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
        args.db = db

        return eyed3_main(args, None)


# info subcommand
class Info(Command):
    def __init__(self, subparsers=None):
        super(Info, self).__init__(
            "info", "Show information about music database.", subparsers)

    def _run(self):
        try:
            db = Database(self.dbinfo)
        except Exception as ex:
            printError(str(ex))
            return 1

        session = db.Session()
        with session.begin():
            printMsg("\nDatabase:")
            printMsg("\tURI: %s" % db._db_uri)
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

        db = Database(self.dbinfo)

        session = db.Session()
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
        db = Database(self.dbinfo)
        session = db.Session()

        s = self.args.search_pattern
        printMsg("\nSearching for '%s'" % s)

        printMsg("Artists:")
        for artist in session.query(Artist).filter(
                Artist.name.ilike(u"%%%s%%" % s)).all():
            printMsg(u"\t%s (id: %d)" % (artist.name, artist.id))

        printMsg("Albums:")
        for album in session.query(Album).filter(
                Album.title.ilike(u"%%%s%%" % s)).all():
            printMsg(u"\t%s (id: %d) (artist: %s)" % (album.title, album.id,
                                                      album.artist.name))

        printMsg("Tracks:")
        for track in session.query(Track).filter(
                Track.title.ilike(u"%%%s%%" % s)).all():
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

    def _handleArgs(self, args):
        dbinfo = super(List, self)._handleArgs(args)
        self.run(dbinfo, args.what)

    def _run(self):
        db = Database(self.dbinfo)

        if self.args.what == "artists":
            banner = None

            session = db.Session()
            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                if banner != artist.sort_name[0]:
                    banner = artist.sort_name[0]
                    printMsg(u"\n== %s ==" % banner)
                printMsg(u"\t%s" % artist.sort_name)
        elif self.args.what == "albums":
            def albumSortKey(alb):
                return alb.release_date

            session = db.Session()
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
        db = Database(self.dbinfo)
        session = db.Session()

        oldroot, newroot = self.args.oldroot, self.args.newroot

        if oldroot[-1] != os.sep:
            oldroot += os.sep
        if newroot[-1] != os.sep:
            newroot += os.sep

        # FIXME: warn if relocated path value does not exist

        num_relocates = 0
        with session.begin():

            for track in session.query(Track).filter(
                    Track.path.like(u"%s%%" % oldroot)).all():
                track.path = track.path.replace(oldroot, newroot)
                num_relocates += 1

            session.flush()
        printMsg("%d files relocated from '%s' to '%s'" %
                 (num_relocates, oldroot, newroot))


_cmds.extend([Init, Sync, Info, Random, Search, List, Relocate])


def makeCmdLineParser():
    from .info import VERSION_MSG

    parser = ArgumentParser(prog="mishmash", version=VERSION_MSG)

    db_group = parser.add_argument_group(title="Database settings and options")

    db_group.add_argument("--db-type", dest="db_type", default="sqlite",
                          help="Database type. Supported types: %s" %
                               ', '.join(SUPPORTED_DB_TYPES))
    db_group.add_argument("--database", dest="db_name",
                          default=None,
                          help="The name of the datbase (path for sqlite).")
    db_group.add_argument("--username", dest="username",
                          default=getpass.getuser(),
                          help="Login name for database. Not used for sqlite. "
                               "Default is the user login name.")
    db_group.add_argument("--password", dest="password", default=None,
                          help="Password for database. Not used for sqlite. ")
    db_group.add_argument("--host", dest="host", default="localhost",
                          help="Hostname for database. Not used for sqlite. "
                               "The default is 'localhost'")
    db_group.add_argument("--port", dest="port", default=5432,
                          help="Port for database. Not used for sqlite.")

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
