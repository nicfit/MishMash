import os
import sys
import traceback

from sqlalchemy import exc as sql_exceptions
from nicfit.console import ansi
from nicfit import Application, ConfigOpts

from eyed3.utils.prompt import PromptExit

from .config import DEFAULT_CONFIG, CONFIG_ENV_VAR, Config, MAIN_SECT, SA_KEY
from . import log
from . core import Command, CommandError
from .commands import *                                                   # noqa

_FORK_METHOD_SET = False


def _pErr(msg):
    print(ansi.Fg.red(str(msg) + ":"))
    tb = sys.exc_info()
    traceback.print_exception(tb[0], tb[1], tb[2])


def main(args):
    import multiprocessing
    global _FORK_METHOD_SET

    if not _FORK_METHOD_SET:
        try:
            multiprocessing.set_start_method("fork")
            _FORK_METHOD_SET = True
        except RuntimeError as ex:
            log.warning("multiprocessing.set_start_method: " + str(ex))

    if not hasattr(args, "command_func") or not args.command_func:
        # No command was given.
        args.app.arg_parser.print_help()
        return 1

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

    # Run command
    try:
        retval = args.command_func(args) or 0
    except (KeyboardInterrupt, PromptExit):
        # PromptExit raised when CTRL+D during prompt, or prompts disabled
        retval = 0
    except (sql_exceptions.ArgumentError,):
        _pErr("Database error")
        retval = 1
    except (sql_exceptions.OperationalError,) as db_err:
        print(str(db_err), file=sys.stderr)
        retval = 1
    except CommandError as cmd_err:
        print(str(cmd_err), file=sys.stderr)
        retval = cmd_err.exit_status
    except Exception as ex:
        log.exception(ex)
        _pErr("General error")
        retval = 2

    return retval


class MishMash(Application):
    def __init__(self, progname="mishmash", ConfigClass=None, config_obj=None):
        from . import version

        if ConfigClass and config_obj:
            raise ValueError("ConfigClass and config_obj are not compatible together.")

        config_opts = ConfigOpts(required=False,
                                 default_config=DEFAULT_CONFIG,
                                 default_config_opt="--default-config",
                                 ConfigClass=ConfigClass or Config,
                                 config_env_var=CONFIG_ENV_VAR,
                                 init_logging_fileConfig=True)
        super().__init__(main, name=progname, version=version,
                         config_opts=config_opts, pdb_opt=False,
                         gettext_domain="MishMash")

        ansi.init()

        desc = "Database command line options (or config) are required by most sub commands."
        subs = self.arg_parser.add_subparsers(title="Commands", dest="command",
                                              description=desc, required=False)
        Command.loadCommandMap(subparsers=subs)
        self.arg_subparsers = subs
        self._user_config = config_obj

    def _main(self, args):
        if self._user_config:
            args.config = self._user_config

        return super()._main(args)

    def _addArguments(self, parser):
        group = parser.add_argument_group(title="Settings and options")
        group.add_argument("-D", "--database", dest="db_url", metavar="url", default=None,
                           help="Database URL. This will override the URL from the config "
                                "file be it the default of one passed with -c/--config.")


app = MishMash()
if __name__ == "__main__":
    app.run()                                                 # pragma: no cover
