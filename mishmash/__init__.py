# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2012  Travis Shirk <travis@pobox.com>
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

__author__ = 'Travis Shirk'
__email__ = 'travis@pobox.com'
__version__ = '0.1.0'
__version_info__   = tuple((int(v) for v in __version__.split('.')))
__release__ = 'alpha'
__web__ = "http://mishmash.nicfit.net/"

__version_txt__     = """
MishMash %(__version__)s-%(__release__)s (C) Copyright %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__web__)s
""" % (locals())

__years__ = "2012-2014"

from .log import log
