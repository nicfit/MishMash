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
import os
from os.path import expandvars
import configparser


CONFIG_ENV_VAR = "MISHMASH_CONFIG"
MAIN_SECT = "mishmash"
SA_KEY = "sqlalchemy.url"


default_str = """
[mishmash]
sqlalchemy.url = %(db_url)s

; Albums that involve a collection of different artists are grouped under
; this name.
various_artists_name = Various Artists

###
# logging configuration
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/logging.html
###

[loggers]
keys = root, sqlalchemy, eyed3, mishmash

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = INFO
handlers = console

[logger_sqlalchemy]
level = WARN
handlers = console
qualname = sqlalchemy.engine
# "level = INFO" logs SQL queries.
# "level = DEBUG" logs SQL queries and results.
# "level = WARN" logs neither.  (Recommended for production systems.)
propagate = 0

[logger_mishmash]
level = INFO
qualname = mishmash
handlers = console
propagate = 0

[logger_eyed3]
level = ERROR
qualname = eyed3
handlers = console
propagate = 0

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(generic_format)s

###
# app configuration
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html
###

[app:main]
use = call:mishmash.web:main

pyramid.reload_templates = true
pyramid.debug_authorization = false
pyramid.debug_notfound = false
pyramid.debug_routematch = false
pyramid.default_locale_name = en
pyramid.includes =
    pyramid_debugtoolbar
    pyramid_tm

[server:main]
use = egg:waitress#main
host = 0.0.0.0
port = 6474

""" % {"db_url": expandvars("sqlite:///$HOME/mishmash.db"),
       "generic_format":
         "%(levelname)-5.5s [%(name)s][%(threadName)s]: %(message)s",
      }


def load(config_file):
    '''Initializes a config with the default, applies ``config_file`` if it is
    not None, and applies any file set in the MISHMASH_CONFIG environment
    variable.'''
    conf = ConfigParser()
    conf.read_string(default_str)

    # -c / --config
    if config_file:
        with open(config_file) as confp:
            conf.read_file(confp)

    # env var
    if CONFIG_ENV_VAR in os.environ:
        with open(os.environ[CONFIG_ENV_VAR]) as confp:
            conf.read_file(confp)

    return conf


class ConfigParser(configparser.ConfigParser):
    def __init__(self):
        super(ConfigParser, self).__init__(
                interpolation=configparser.ExtendedInterpolation())

    # XXX: new decorator could simplify these accessors.

    @property
    def db_url(self):
        return self.get(MAIN_SECT, SA_KEY)

    @property
    def various_artists_name(self):
        return self.get(MAIN_SECT, "various_artists_name")


default = ConfigParser()
default.read_string(default_str)
