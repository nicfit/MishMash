# -*- coding: utf-8 -*-
from collections import namedtuple

__version__ = '0.2.0-beta4'
__release_name__ = ""
__release__ = __version__.split('-')[1] if '-' in __version__ else "final"

__project_name__ = 'mishmash'
__project_slug__ = 'mishmash'
__author__ = 'Travis Shirk'
__author_email__ = 'travis@pobox.com'
__url__ = 'https://github.com/nicfit/mishmash'
__description__ = 'Mu'

__version_info__ = \
    namedtuple("Version", "major, minor, maint, release")(
        *(tuple((int(v) for v in __version__.split('-')[0].split('.'))) +
          tuple((__release__,))))

__years__ = "2014-2016"
__license__ = 'GNU GPL v3.0'

__version_txt__ = """
%(__name__)s %(__version__)s (C) Copyright %(__years__)s %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__url__)s
""" % (locals())
