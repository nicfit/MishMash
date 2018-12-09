# XXX: revist, but this going away is nice
import warnings
warnings.filterwarnings("ignore", message="The psycopg2 wheel package will be renamed")

from nicfit import getLogger
from .orm import VARIOUS_ARTISTS_NAME
from .__about__ import __version__ as version

log = getLogger(__package__)


__all__ = ["log", "getLogger", "version", "VARIOUS_ARTISTS_NAME"]
