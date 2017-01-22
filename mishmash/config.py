# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2014  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################
from pathlib import Path
import nicfit


WEB_PORT = 6229
MAIN_SECT = "mishmash"
SA_KEY = "sqlalchemy.url"
CONFIG_ENV_VAR = "MISHMASH_CONFIG"
SQLITE_DB_URL = "sqlite:///{0}/mishmash.db".format(Path.home())
POSTGRES_DB_URL = "postgresql://mishmash@localhost/mishmash"
LOG_FORMAT = "<%(name)s:%(threadName)s> [%(levelname)s]: %(message)s"
VARIOUS_ARTISTS_TEXT = "Various Artists"


def DEFAULT_CONFIG():
    from .orm import MAIN_LIB_NAME
    default = Path(__file__).parent / "_default-config.ini"
    return default.read_text().format(MAIN_LIB_NAME=MAIN_LIB_NAME, **globals())


class Config(nicfit.Config):
    def __init__(self, filename, **kwargs):
        from configparser import ExtendedInterpolation
        super().__init__(filename, interpolation=ExtendedInterpolation(),
                         **kwargs)

    # XXX: new decorator could simplify these accessors.
    @property
    def db_url(self):
        return self.get(MAIN_SECT, SA_KEY)

    @property
    def various_artists_name(self):
        return self.get(MAIN_SECT, "various_artists_name")

    @property
    def music_libs(self):
        from .library import MusicLibrary

        for sect in [s for s in self.sections() if s.startswith("library:")]:
            yield MusicLibrary.fromConfig(self[sect])
