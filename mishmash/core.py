from nicfit import getLogger
from nicfit.command import Command as BaseCommand
from nicfit.command import CommandError
# FIXME: eyeD3 0.8.5
# from eyed3.core import EP_MAX_SIZE_HINT
EP_MAX_SIZE_HINT = 6

__all__ = ["Command", "CommandError", "EP_MAX_SIZE_HINT"]
log = getLogger(__name__)


class Command(BaseCommand):
    """Base class for MishMash commands."""

    def run(self, args, config):
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
