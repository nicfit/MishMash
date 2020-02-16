# XXX: revist, but this going away is nice
import warnings
warnings.filterwarnings("ignore", message="The psycopg2 wheel package will be renamed")

from nicfit import getLogger                                               # noqa: E402
from .orm.core import VARIOUS_ARTISTS_NAME                                 # noqa: E402
from .__about__ import __version__ as version                              # noqa: E402

log = getLogger(__package__)


__all__ = ["log", "getLogger", "version", "VARIOUS_ARTISTS_NAME"]
