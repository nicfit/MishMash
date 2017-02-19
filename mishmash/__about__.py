# -*- coding: utf-8 -*-
from collections import namedtuple


def __parse_version(v):
    for c in ("a", "b", "c"):
        parsed = v.split(c)
        if len(parsed) == 2:
            return (parsed[0], c + parsed[1])
    return v, "final"


__version__ = "0.3a0"
__release_name__ = "Nine Patriotic Hymns For Children"
__years__ = "2013-2017"

__project_name__ = "MishMash"
__project_slug__ = "mishmash"
__pypi_name__ = "MishMash"
__author__ = "Travis Shirk"
__author_email__ = "travis@pobox.com"
__url__ = "https://github.com/nicfit/MishMash"
__description__ = "Music database and web interface."
__long_description__ = ""
__license__ = "GNU GPL v3.0"
__github_url__ = "https://github.com/nicfit/mishmash",

__release__ = __parse_version(__version__)[1]
_v = tuple((int(v) for v in __parse_version(__version__)[0].split(".")))
__version_info__ = \
    namedtuple("Version", "major, minor, maint, release")(
        *(_v + (tuple((0,)) * (3 - len(_v))) +
          tuple((__release__,))))
del _v
__version_txt__ = """
%(__name__)s %(__version__)s (C) Copyright %(__years__)s %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__url__)s
""" % (locals())
