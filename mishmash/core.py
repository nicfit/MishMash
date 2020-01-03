from eyed3.core import EP_MAX_SIZE_HINT
from nicfit import getLogger
from nicfit.command import Command as BaseCommand, CommandError

__all__ = ["Command", "CommandError", "EP_MAX_SIZE_HINT"]
log = getLogger(__name__)


class Command(BaseCommand):
    """Base class for MishMash commands."""
    _library_arg_nargs = None  # '*', '+', '?', None, 1

    config = None
    db_conn = None
    db_engine = None
    db_session = None

    def _initArgParser(self, parser):
        super()._initArgParser(parser)

        if self._library_arg_nargs:
            from .util import addLibraryArguments
            addLibraryArguments(parser, self._library_arg_nargs)

    def run(self, args):
        from . import database

        self.config = args.config

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
