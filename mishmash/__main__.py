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
import logging
import logging.config
from argparse import ArgumentParser

from sqlalchemy import exc as sql_exceptions

import eyed3
eyed3.require("0.8")

from eyed3.utils.console import AnsiCodes
from eyed3.utils.console import Fore as fg
from eyed3.utils.prompt import PromptExit

from .database import MissingSchemaException
from .log import log
from . import config
from .commands.command import Command


def _pErr(subject, msg):
    print(fg.red(subject) + ": %s" % str(msg))


def makeCmdLineParser():
    from . import __version_txt__ as VERSION_MSG

    parser = ArgumentParser(prog="mishmash")
    parser.add_argument("--version", action="version", version=VERSION_MSG)

    group = parser.add_argument_group(title="Settings and options")
    group.add_argument("-c", "--config", dest="config", metavar="config.ini",
                       default=None, help="Configuration file.")
    group.add_argument("--default-config", dest="show_config",
                       action="store_true",
                       help="Prints the default configuration.")
    group.add_argument("-D", "--database", dest="db_url", metavar="url",
            default=None,
            help="Database URL. This will override the URL from the config "
                 "file be it the default of one passed with -c/--config.")

    subparsers = parser.add_subparsers(
            title="Sub commands",
            description="Database command line options are required by most "
                        "sub commands.")

    # 'help' subcommand; turns it into the less intuitive --help format.
    def _help(args, config):
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


def main():
    parser = makeCmdLineParser()
    parser.add_argument("--pdb", action="store_true", dest="debug_pdb",
                        help="Drop into 'pdb' when errors occur.")

    args = parser.parse_args()
    if args.show_config:
        print(config.DEFAULT_CONFIG)
        return 0
    elif "func" not in args:
        # No command was given.
        parser.print_help()
        return 1

    if args.debug_pdb:
        try:
            # The import of ipdb MUST be limited to explicit --pdb option
            # (thius code SHOULD (and was) at module scope) but because of
            # https://github.com/gotcha/ipdb/issues/48 it is here. When --pdb is
            # used with commands where stdout is captured you will get extra
            # leading bytes.
            import ipdb as pdb
        except ImportError:
            import pdb

        def _pdb():
            e, m, tb = sys.exc_info()
            pdb.post_mortem(tb)
    else:
        def _pdb():
            pass

    app_config, args.config_files = config.load(args.config)

    logging.config.fileConfig(app_config)

    if args.db_url:
        app_config.set(config.MAIN_SECT, config.SA_KEY, args.db_url)
        # Don't want commands and such to use this, so reset.
        args.db_url = None

    AnsiCodes.init(True)

    try:
        # Run command
        retval = args.func(args, app_config) or 0
    except (KeyboardInterrupt, PromptExit) as ex:
        # PromptExit raised when CTRL+D during prompt, or prompts disabled
        retval = 0
    except (sql_exceptions.ArgumentError,
            sql_exceptions.OperationalError) as ex:
        _pErr("Database error", ex)
        _pdb()
        retval = 1
    except MissingSchemaException as ex:
        _pErr("Schema error",
              "The table%s '%s' %s missing from the database schema." %
                 ('s' if len(ex.tables) > 1 else '',
                  ", ".join([str(t) for t in ex.tables]),
                  "are" if len(ex.tables) > 1 else "is")
             )
        retval = 1
    except Exception as ex:
        log.exception(ex)
        _pErr(ex.__class__.__name__, str(ex))
        _pdb()
        retval = 2

    return retval


if __name__ == "__main__":
    sys.exit(main())
