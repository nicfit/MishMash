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

    if args.debug_pdb:
        try:
            # The import of ipdb MUST be limited to explicit --pdb option
            # (this code SHOULD (and was) at module scope) but because of
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

    # env var config file
    if CONFIG_ENV_VAR in os.environ:
        with open(os.environ[CONFIG_ENV_VAR]) as confp:
            args.config.read_file(confp)

    logging.config.fileConfig(args.config)

    if args.db_url:
        args.config.set(config.MAIN_SECT, config.SA_KEY, args.db_url)
        # Don't want commands and such to use this, so reset.
        args.db_url = None

    AnsiCodes.init(True)

    try:
        # Run command
        retval = args.func(args, args.config) or 0
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


class MishMash(Application):
    def __init__(self):
        from . import __version__
        super().__init__(main, name="mishmash", version=__version__,
                         config_opts=ConfigOpts(required=False,
                                                default_config=DEFAULT_CONFIG,
                                                ConfigClass=Config))

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

        parser.add_argument("--pdb", action="store_true", dest="debug_pdb",
                            help="Drop into 'pdb' when errors occur.")

        return parser

if __name__ == "__main__":
    MishMash().run()
