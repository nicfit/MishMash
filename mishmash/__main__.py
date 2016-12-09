# -*- coding: utf-8 -*-
import os
import sys
import logging
import logging.config
from argparse import ArgumentParser

from nicfit import Application, ConfigOpts
from sqlalchemy import exc as sql_exceptions

import eyed3

from eyed3.utils.console import AnsiCodes
from eyed3.utils.console import Fore as fg
from eyed3.utils.prompt import PromptExit

from .database import MissingSchemaException
from .config import DEFAULT_CONFIG, CONFIG_ENV_VAR, Config
from .commands.command import Command
from . import log

eyed3.require("0.8")


def _pErr(subject, msg):
    print(fg.red(subject) + ": %s" % str(msg))


def main(args):

    if args.show_config:
        print(DEFAULT_CONFIG)
        return 0
    elif "func" not in args:
        # No command was given.
        args.app.arg_parser.print_help()
        return 1


class MishMash(Application):
    def __init__(self):
        from . import __version__
        super().__init__(main, name="mishmash", version=__version__,
                         config_opts=ConfigOpts(required=False,
                                                default_config=DEFAULT_CONFIG,
                                                ConfigClass=Config),
                         pdb_opt=True)

    def _addArguments(self, parser):
        group = parser.add_argument_group(title="Settings and options")
        # XXX: Move this to ConfigOpts and ArgumentParser??
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

if __name__ == "__main__":
    MishMash().run()
