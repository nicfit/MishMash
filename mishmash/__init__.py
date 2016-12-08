# -*- coding: utf-8 -*-
import nicfit


__projectname__ = 'MishMash'
__author__ = 'Travis Shirk'
__email__ = 'travis@pobox.com'
__web__ = 'http://mishmash.nicfit.net/'

__version__ = '0.1.0'
__version_info__ = tuple((int(v) for v in __version__.split('.')))
__release__ = 'alpha'
__years__ = '2014'

__version_txt__ = """
%(__projectname__)s %(__version__)s-%(__release__)s (C) Copyright %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__web__)s
""" % (locals())

log = nicfit.getLogger(__package__)
