from pathlib import Path
from configparser import ExtendedInterpolation
import nicfit
from .orm import MAIN_LIB_NAME

WEB_PORT = 6229
MAIN_SECT = "mishmash"
SA_KEY = "sqlalchemy.url"
CONFIG_ENV_VAR = "MISHMASH_CONFIG"
SQLITE_DB_URL = "sqlite:///{0}/mishmash.db".format(Path().cwd())
POSTGRES_DB_URL = "postgresql://mishmash@localhost/mishmash"
LOG_FORMAT = "<%(name)s:%(threadName)s> [%(levelname)s]: %(message)s"

LOGGING_CONFIG = (
    nicfit.logger.FileConfig(level="WARNING")
                 .addPackageLogger("alembic")
                 .addPackageLogger("mishmash")
                 .addPackageLogger("eyed3", pkg_level="ERROR")
                 .addHandler("file", "StreamHandler", args=("sys.stderr",))
)

DEFAULT_CONFIG = f"""
[mishmash]
sqlalchemy.url = {SQLITE_DB_URL}
;sqlalchemy.url = {POSTGRES_DB_URL}

# All sync'd media is assigned to the '{MAIN_LIB_NAME}' library unless
# instructed
;[library:{MAIN_LIB_NAME}]
;sync = true
;paths = dir1
;        dir2
;        dir_glob
# Directories to exclude, each as a regex
;excludes = dir_regex1
;           dir_regex2


[app:main]
use = call:mishmash.web:main
pyramid.reload_templates = true
pyramid.default_locale_name = en
pyramid.includes =
    pyramid_tm
# Devel opts
;pyramid.debug_authorization = false
;pyramid.debug_notfound = false
;pyramid.debug_routematch = false
;pyramid.includes =
;    pyramid_debugtoolbar
;    pyramid_tm

[server:main]
use = egg:waitress#main
host = 0.0.0.0
port = {WEB_PORT}

{LOGGING_CONFIG}
"""


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
