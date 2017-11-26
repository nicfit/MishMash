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
    # TODO: dev config option?
    default = Path(__file__).parent / "_default-config.ini"
    return default.read_text().format(MAIN_LIB_NAME=MAIN_LIB_NAME, **globals())


class MusicLibrary:
    def __init__(self, name, paths=None, excludes=None, sync=True):
        self.name = name
        self.paths = paths or []
        self.sync = sync
        self.excludes = excludes

    @staticmethod
    def fromConfig(config):
        all_paths = []
        paths = config.get("paths")
        if paths:
            paths = paths.split("\n")
            for p in [Path(p).expanduser() for p in paths]:
                glob_paths = [
                    str(p) for p in Path("/").glob(str(p.relative_to("/")))
                ]
                all_paths += glob_paths if glob_paths else [str(p)]

        excludes = [str(Path(p).expanduser())
                        for p in config.getlist("excludes", fallback=[])]

        return MusicLibrary(config.name.split(":", 1)[1], paths=all_paths,
                            excludes=excludes,
                            sync=config.getboolean("sync", True))


class Config(nicfit.Config):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, interpolation=ExtendedInterpolation(),
                         **kwargs)

    # XXX: new decorator could simplify these accessors.
    @property
    def db_url(self):
        return self.get(MAIN_SECT, SA_KEY).strip()

    @property
    def music_libs(self):
        for sect in [s for s in self.sections() if s.startswith("library:")]:
            yield MusicLibrary.fromConfig(self[sect])
