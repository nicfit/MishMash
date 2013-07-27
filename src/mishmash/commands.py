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

import eyed3
eyed3.require("0.7.4")

import eyed3.main
from eyed3.main import main as eyed3_main
from eyed3.utils.cli import printError, printMsg, printWarning

from .database import SUPPORTED_DB_TYPES, Database, MissingSchemaException
from .orm import Track, Artist, Album, Meta, Label
from .log import log


_cmds = []


class Command(object):
    cmds = {}
    
    def __init__(self, subparsers, name, help):
        self.subparsers = subparsers
        self.parser = self.subparsers.add_parser(name, help=help)
        self.parser.set_defaults(func=self.run)
        self.cmds[name] = self

    def makeDatabase(self, args, do_create=False):
        return Database(args.db_type, args.db_name,
                        username=args.username, password=args.password,
                        host=args.host, port=args.port,
                        do_create=do_create)
    
    def run(self, args):
        raise Exception("Must implement the run() function")

    @staticmethod
    def initAll(subparsers):
        for cmd in _cmds:
            cmd(subparsers)


# init subcommand
class Init(Command):
    def __init__(self, subparsers):
        super(Init, self).__init__(subparsers, "init",
                                   "Initialize music database.")
        self.parser.add_argument("--drop-all", action="store_true",
                                 help="Drop all tables and re-init")

    def run(self, args):
        try:
            db = self.makeDatabase(args, False)
        except MissingSchemaException as ex:
            db = None

        dropped = False
        if db and args.drop_all:
            printWarning("Dropping all database tables.")
            db.dropAllTables()
            dropped = True

        if not db or dropped:
            printMsg("Initializing...")
            db = self.makeDatabase(args, True)
    

# sync subcommand
class Sync(Command):
    def __init__(self, subparsers):
        super(Sync, self).__init__(subparsers, "sync",
                                   "Syncronize music and database.")
        from . import sync
        self.parser = eyed3.main.makeCmdLineParser(self.parser)
        self.plugin = sync.SyncPlugin(self.parser)

    def run(self, args):
        db = self.makeDatabase(args)
        args.db = db

        return eyed3_main(args, None)


# info subcommand
class Info(Command):
    def __init__(self, subparsers):
        super(Info, self).__init__(subparsers, "info",
                                   "Show information about music database.")

    def run(self, args):
        db = self.makeDatabase(args)
            
        session = db.Session()
        with session.begin():
            print("\nDatabase:")
            print("URI: %s" % db._db_uri)
            meta = session.query(Meta).one()
            print("Version:", meta.version)
            print("Last Sync:", meta.last_sync)
            print("%d tracks" % session.query(Track).count())
            print("%d artists" % session.query(Artist).count())
            print("%d albums" % session.query(Album).count())
            print("%d labels" % session.query(Label).count())
    

# random subcommand
class Random(Command):
    def __init__(self, subparsers):
        super(Random, self).__init__(subparsers, "random",
                                     "Retrieve random tracks.")
        self.parser.add_argument("count", type=int, metavar="COUNT")

    def run(self, args):
        from sqlalchemy.sql.expression import func
            
        db = self.makeDatabase(args)
            
        session = db.Session()
        for track in session.query(Track).order_by(func.random())\
                                         .limit(args.count).all():
            printMsg(track.path)


class Search(Command):
    def __init__(self, subparsers):
        super(Search, self).__init__(subparsers, "search",
                                     "Search music database.")
        self.parser.add_argument("search_pattern", type=unicode,
                                 metavar="SEARCH", help="Search string.")

    def run(self, args):
        db = self.makeDatabase(args)
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


class List(Command):
    def __init__(self, subparsers):
        super(List, self).__init__(subparsers, "list",
                                   "Listings from music database.")
        list_choices = ("artists", "albums")
        self.parser.add_argument(
            "what", metavar="WHAT", choices=list_choices,
            help="What to list. Valid values are %s." %
                 ','.join(["'%s'" % c for c in list_choices]))

    def run(self, args):
        db = self.makeDatabase(args)
    
        if args.what == "artists":
            banner = None
    
            session = db.Session()
            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                if banner != artist.sort_name[0]:
                    banner = artist.sort_name[0]
                    printMsg(u"\n== %s ==" % banner)
                printMsg(u"\t%s" % artist.sort_name)
        elif args.what == "albums":
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
    def __init__(self, subparsers):
        super(Relocate, self).__init__(
            subparsers,"relocate",
            "Relocate file paths from one root prefix to another")
        self.parser.add_argument("oldroot", help="The path to replace.")
        self.parser.add_argument("newroot", help="The substitute path.")

    def run(self, args):
        db = self.makeDatabase(args)
        session = db.Session()
    
        old, new = args.oldroot, args.newroot
        if old[-1] != os.sep:
            old += os.sep
        if new[-1] != os.sep:
            new += os.sep
    
        num_relocates = 0
        with session.begin():
    
            for track in session.query(Track).filter(
                    Track.path.like(u"%s%%" % old)).all():
                track.path = track.path.replace(old, new)
                num_relocates += 1
    
            session.flush()
        print("%d files relocated from '%s' to '%s'" % (num_relocates, old, new))


_cmds.extend([Init, Sync, Info, Random, Search, List, Relocate])
