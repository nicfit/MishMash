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
import logging

class DefaultFormatter(logging.Formatter):
    DEFAULT_FORMAT = '<%(name)s> [%(levelname)s]: %(message)s'

    def __init__(self):
        logging.Formatter.__init__(self, self.DEFAULT_FORMAT)

log = logging.getLogger("mishmash")

def setupLogging():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(DefaultFormatter())
    log.addHandler(console_handler)

    log.setLevel(logging.NOTSET)
    log.propagate = False
