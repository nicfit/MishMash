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
import tempfile
from pyramid.scripts.pserve import PServeCommand
from . import command


@command.register
class Web(command.Command):
    NAME = "web"

    def __init__(self, subparsers=None):
        super(Web, self).__init__("MishMash web interface.", subparsers)

    def _run(self):
        # pserve wants a file to open, so use the *composed* config.
        with tempfile.NamedTemporaryFile(mode="w") as config_file:
            self.config.write(config_file)
            config_file.flush()
            argv = ["mishmish", config_file.name]
            pserve = PServeCommand(argv)
            return pserve.run()
