# -*- coding: utf-8 -*-
import os
import sys
import logging
import logging.config
import traceback

from sqlalchemy import exc as sql_exceptions
from nicfit.console import ansi
from nicfit import Application, ConfigOpts

from eyed3.utils.prompt import PromptExit

from .config import DEFAULT_CONFIG, CONFIG_ENV_VAR, Config, MAIN_SECT, SA_KEY
from . import log
from .commands import *                                                   # noqa


def _pErr(msg):
    print(ansi.Fg.red(str(msg) + ":"))
    tb = sys.exc_info()
    traceback.print_exception(tb[0], tb[1], tb[2])


def main(args):
    import multiprocessing

    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError as ex:
        log.warn("multiprocessing.set_start_method: " + str(ex))

    if not args.command:
        # No command was given.
        args.app.arg_parser.print_help()
        return 1

    logging.config.fileConfig(args.config)
    # In the case fileConfig undid the command line, which has precedence.
    args.applyLoggingOpts(args.log_levels, args.log_files)

    if args.db_url:
        args.config.set(MAIN_SECT, SA_KEY, args.db_url)
        # Don't want commands and such to use this, so reset.
        args.db_url = None
    elif "MISHMASH_DBURL" in os.environ:
        log.verbose("Using environment MISHMASH_DBURL over configuration: {}"
                    .format(os.environ["MISHMASH_DBURL"]))
        args.config.set(MAIN_SECT, SA_KEY, os.environ["MISHMASH_DBURL"])

    try:
        # Run command
        retval = args.command_func(args, args.config) or 0
    except (KeyboardInterrupt, PromptExit) as ex:
        # PromptExit raised when CTRL+D during prompt, or prompts disabled
        retval = 0
    except (sql_exceptions.ArgumentError,
            sql_exceptions.OperationalError) as ex:
        _pErr("Database error")
        retval = 1
    except Exception as ex:
        log.exception(ex)
        _pErr("General error")
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
                         config_opts=config_opts, pdb_opt=True,
                         gettext_domain="MishMash")

        ansi.init()

        desc = "Database command line options (or config) are required by "\
               "most sub commands."
        self.enableCommands(title="Commands", description=desc)

    def _addArguments(self, parser):
        group = parser.add_argument_group(title="Settings and options")
        group.add_argument("-D", "--database", dest="db_url", metavar="url",
                default=None,
                help="Database URL. This will override the URL from the config "
                     "file be it the default of one passed with -c/--config.")


app = MishMash()
if __name__ == "__main__":
    app.run()                                                 # pragma: no cover
