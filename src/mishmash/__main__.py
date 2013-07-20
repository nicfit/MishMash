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

import sys
import getpass
from datetime import datetime

import eyed3
eyed3.require("0.7.4")

import eyed3.main
from eyed3.main import main as eyed3_main
from eyed3.utils.cli import ArgumentParser
from eyed3.utils.cli import printError, printMsg, printWarning

from .database import SUPPORTED_DB_TYPES, Database, MissingSchemaException
from .orm import Track, Artist, Album, Meta, Label


def _makeDatabase(args, do_create=False):
    return Database(args.db_type, args.db_name,
                    username=args.username, password=args.password,
                    host=args.host, port=args.port,
                    do_create=do_create)


def _init(args):

    try:
        db = _makeDatabase(args, False)
    except MissingSchemaException as ex:
        db = None

    if db and args.drop_all:
        printWarning("Dropping all database tables.")
        db.dropAllTables()

    db = _makeDatabase(args, True)
    printMsg("Database initialized")


def _sync(args):
    db = _makeDatabase(args)
    args.db = db

    return eyed3_main(args, None)


def _info(args):
    # FIXME: show database parameters
    db = _makeDatabase(args)

    session = db.Session()
    with session.begin():
        print("\nDatabase:")
        meta = session.query(Meta).one()
        print("Version:", meta.version)
        print("Last Sync:", meta.last_sync)
        meta.last_sync = datetime.now()
        print("%d tracks" % session.query(Track).count())
        print("%d artists" % session.query(Artist).count())
        print("%d albums" % session.query(Album).count())
        print("%d labels" % session.query(Label).count())


def _random(args):
    from sqlalchemy.sql.expression import func

    db = _makeDatabase(args)

    session = db.Session()
    for track in session.query(Track).order_by(func.random())\
                                     .limit(args.count).all():
        printMsg(track.path)


def _search(args):
    db = _makeDatabase(args)
    session = db.Session()

    s = args.search_pattern
    printMsg("\nSearching for '%s'" % s)

    print("Artists:")
    for artist in session.query(Artist).filter(
            Artist.name.ilike(u"%%%s%%" % s)).all():
        printMsg(u"\t%s (id: %d)" % (artist.name, artist.id))

    print("Albums:")
    for album in session.query(Album).filter(
            Album.title.ilike(u"%%%s%%" % s)).all():
        printMsg(u"\t%s (id: %d) (artist: %s)" % (album.title, album.id,
                                                  album.artist.name))

    print("Tracks:")
    for track in session.query(Track).filter(
            Track.title.ilike(u"%%%s%%" % s)).all():
        printMsg(u"\t%s (id: %d) (artist: %s) (album: %s)" %
                 (track.title, track.id,
                  track.artist.name,
                  track.album.title if track.album else None))


def _list(args):
    db = _makeDatabase(args)

    if args.what == "artists":
        banner = None

        session = db.Session()
        for artist in session.query(Artist)\
                             .order_by(Artist.sort_name).all():
            if banner != artist.sort_name[0]:
                banner = artist.sort_name[0]
                printMsg(u"\n== %s ==" % banner)
            printMsg(u"\t%s" % artist.sort_name)
    else:
        # This should not happen if ArgumentParser is doing its job
        assert(not "unsupported list value")


def main():

    parser = ArgumentParser(prog="mishmash")

    db_group = parser.add_argument_group(title="Database settings and options")

    db_group.add_argument("--db-type", dest="db_type", default="sqlite",
                          help="Database type. Supported types: %s" %
                               ', '.join(SUPPORTED_DB_TYPES))
    db_group.add_argument("--database", dest="db_name",
                          default="mishmash.db",
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
    def mkSubParser(name, help, func):
        p = subparsers.add_parser(name, help=help)
        p.set_defaults(func=func)
        return p

    # init subcommand
    init_parser = mkSubParser("init", "Initialize music database.", _init)
    init_parser.add_argument("--drop-all", action="store_true",
                             help="Drop all tables and re-init")

    # sync subcommand
    from . import sync
    sync_parser = eyed3.main.makeCmdLineParser(
            mkSubParser("sync", "Syncronize music and database.", _sync))
    plugin = sync.SyncPlugin(sync_parser)

    # info subcommand
    info_parser = mkSubParser("info","Show information about music database.",
                               _info)

    # random subcommand
    random_parser = mkSubParser("random", "Retrieve random tracks.", _random)
    random_parser.add_argument("count", type=int, metavar="COUNT")

    # search subcommand
    search_parser = mkSubParser("search", "Search music database.", _search)
    search_parser.add_argument("search_pattern", type=unicode, metavar="SEARCH",
                               help="Search string.")

    # list subcommand
    list_choices = ("artists",)
    list_parser = mkSubParser("list", "Listings from music database.", _list)
    list_parser.add_argument("what", metavar="WHAT", choices=list_choices,
                             help="What to list. Valid values are %s." %
                                  ','.join(["'%s'" % c for c in list_choices]))

    # Run command
    args = parser.parse_args()
    args.plugin = plugin
    try:
        retval = args.func(args) or 0
    except MissingSchemaException as ex:
        printError("Schema error:")
        printMsg("The table%s '%s' %s missing from the database schema." %
                 ('s' if len(ex.tables) > 1 else '',
                  ", ".join(ex.tables),
                  "are" if len(ex.tables) > 1 else "is"))
        retval = 1
    except Exception as ex:
        printError("%s: %s" % (ex.__class__.__name__, str(ex)))
        retval = 2

    return retval


if __name__ == "__main__":
    sys.exit(main())
