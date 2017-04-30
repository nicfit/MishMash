from pathlib import Path
from configparser import ExtendedInterpolation
import nicfit

WEB_PORT = 6229
MAIN_SECT = "mishmash"
SA_KEY = "sqlalchemy.url"
CONFIG_ENV_VAR = "MISHMASH_CONFIG"
SQLITE_DB_URL = "sqlite:///{0}/mishmash.db".format(Path.home())
POSTGRES_DB_URL = "postgresql://mishmash@localhost/mishmash"
LOG_FORMAT = "<%(name)s:%(threadName)s> [%(levelname)s]: %(message)s"


def DEFAULT_CONFIG():
    from .orm import MAIN_LIB_NAME
    default = Path(__file__).parent / "_default-config.ini"
    return default.read_text().format(MAIN_LIB_NAME=MAIN_LIB_NAME, **globals())


class Config(nicfit.Config):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, interpolation=ExtendedInterpolation(),
                         **kwargs)
        self.add_section(MAIN_SECT)

    # XXX: new decorator could simplify these accessors.
    @property
    def db_url(self):
        return self.get(MAIN_SECT, SA_KEY)

    @property
    def music_libs(self):
        from .library import MusicLibrary

        for sect in [s for s in self.sections() if s.startswith("library:")]:
            yield MusicLibrary.fromConfig(self[sect])
