from nicfit import getLogger
from nicfit.command import Command as BaseCommand, CommandError
from .orm import MAIN_LIB_NAME
# FIXME: eyeD3 0.8.5
# from eyed3.core import EP_MAX_SIZE_HINT
EP_MAX_SIZE_HINT = 6

__all__ = ["Command", "CommandError", "EP_MAX_SIZE_HINT"]
log = getLogger(__name__)


class Command(BaseCommand):
    """Base class for MishMash commands."""
    _library_arg_nargs = None  # '*', '+', '?', None, 1

    def _initArgParser(self, parser):
        super()._initArgParser(parser)

        if self._library_arg_nargs:
            req = self._library_arg_nargs in ("+", 1)
            if self._library_arg_nargs not in ("?", 1):
                action, default, dest = ("append",
                                         [] if not req else [MAIN_LIB_NAME],
                                         "libs")
            else:
                action, default, dest = ("store",
                                         None if not req else MAIN_LIB_NAME,
                                         "lib")

            parser.add_argument("-L", "--library", dest=dest, required=req,
                                action=action, metavar="LIB_NAME",
                                default=default,
                                help="Specify a library.")

    def run(self, args, config):
        import ipdb; ipdb.set_trace()   # FIXME
        from . import database

        self.config = config

        (self.db_engine,
         SessionMaker,
         self.db_conn) = database.init(self.config.db_url)

        self.db_session = SessionMaker()

        try:
            retval = super().run(args)
            self.db_session.commit()
        except Exception:
            self.db_session.rollback()
            raise
        finally:
            self.db_session.close()
            self.db_conn.close()

        return retval
