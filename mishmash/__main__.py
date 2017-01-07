# -*- coding: utf-8 -*-
import logging
import logging.config

from nicfit import Application, ConfigOpts
from sqlalchemy import exc as sql_exceptions


import eyed3

from eyed3.utils.console import AnsiCodes
from eyed3.utils.console import Fore as fg
from eyed3.utils.prompt import PromptExit

from .database import MissingSchemaException
from .config import DEFAULT_CONFIG, CONFIG_ENV_VAR, Config, MAIN_SECT, SA_KEY
from .commands.command import Command
from . import log

eyed3.require("0.8")


def _pErr(subject, msg):
    print(fg.red(subject) + ": %s" % str(msg))


def main(args):
    if "func" not in args:
        # No command was given.
        args.app.arg_parser.print_help()
        return 1

    logging.config.fileConfig(args.config)
    # In the case fileConfig undid the command line, typically not necessary.
    args.applyLoggingOpts(args.log_levels, args.log_files)

    if args.db_url:
        args.config.set(MAIN_SECT, SA_KEY, args.db_url)
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
        retval = 2

    return retval


class MishMash(Application):
    def __init__(self):
        from . import version
        config_opts = ConfigOpts(required=False,
                                 default_config=DEFAULT_CONFIG(),
                                 default_config_opt="--default-config",
                                 ConfigClass=Config, env_var=CONFIG_ENV_VAR)
        super().__init__(main, name="mishmash", version=version,
                         config_opts=config_opts, pdb_opt=True)

    def _addArguments(self, parser):
        group = parser.add_argument_group(title="Settings and options")
        group.add_argument("-D", "--database", dest="db_url", metavar="url",
                default=None,
                help="Database URL. This will override the URL from the config "
                     "file be it the default of one passed with -c/--config.")

        subs = parser.add_subparsers(title="Sub commands", add_help_subcmd=True,
                description="Database command line options are required by most"
                            " sub commands.")
        Command.initAll(subs)

        return parser

app = MishMash()
if __name__ == "__main__":
    app.run()
