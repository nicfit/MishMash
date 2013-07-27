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
from .log import log
from .commands import Command


def main():

    parser = ArgumentParser(prog="mishmash")

    db_group = parser.add_argument_group(title="Database settings and options")

    db_group.add_argument("--db-type", dest="db_type", default="sqlite",
                          help="Database type. Supported types: %s" %
                               ', '.join(SUPPORTED_DB_TYPES))
    db_group.add_argument("--database", dest="db_name",
                          default=os.path.expandvars("${HOME}/mishmash.db"),
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

    # Run command
    args = parser.parse_args()
    args.plugin = Command.cmds["sync"].plugin
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
        log.exception(ex)
        printError("%s: %s" % (ex.__class__.__name__, str(ex)))
        retval = 2

    return retval


if __name__ == "__main__":
    sys.exit(main())
