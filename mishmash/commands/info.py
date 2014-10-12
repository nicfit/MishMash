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
import sys
from pyfiglet import figlet_format
from sqlalchemy.exc import ProgrammingError, OperationalError
from eyed3.utils.console import printError
from eyed3.utils.console import cprint, cformat, Fore, Style
from .. import __version__
from ..orm import Track, Artist, Album, Meta, Label
from . import command


@command.register
class Info(command.Command):
    NAME = "info"

    def __init__(self, subparsers=None):
        super(Info, self).__init__("Show information about the database or "
                                   "configuration.", subparsers)
        self.parser.add_argument("-C", "--show-config", action="store_true",
                                 dest="show_config",
                                 help="Display current configuration.")
        self.parser.add_argument("-D", "--show-default", action="store_true",
                                 dest="show_default",
                                 help="Display the default configuration.")

    def _config(self):
        if self.args.show_default:
            from .. import config
            print(config.default_str)
        else:
            self.config.write(sys.stdout)

    def _info(self):
        session = self.db_session

        _output = []
        def _addOutput(_k, _v):
            _output.append(tuple((_k, _v)))

        def _printOutput(_format, _olist, key_fg=None):
            k_width = max([len(k) for k, v in _olist if k])
            for k, v in _olist:
                print(_format % (cformat(k.ljust(k_width), key_fg), v)
                        if k else "")
            _olist.clear()

        cprint(figlet_format("``MishMash``", font="graffiti"), Fore.GREEN,
                styles=[Style.BRIGHT])

        _addOutput("Version", __version__)
        _addOutput("Database URL", self.config.db_url)

        try:
            meta = session.query(Meta).one()
        except (ProgrammingError, OperationalError) as ex:
            printError("\nError querying metadata. Database may not be "
                       "initialized: %s" % str(ex))
            return 1

        _addOutput("Database version", meta.version)
        _addOutput("Last sync", meta.last_sync)
        _addOutput("Configuration files",
                   (", ".join(self.args.config_files) or "None"))
        _printOutput("%s : %s", _output, key_fg=Fore.BLUE)

        _addOutput(None, None)
        for name, orm_type in [("tracks", Track), ("artists", Artist),
                              ("albums", Album), ("labias", Label),
                     ]:
            count = session.query(orm_type).count()
            _addOutput(str(count), name)
        _printOutput("%s music %s", _output)


    def _run(self):
        if self.args.show_config or self.args.show_default:
            self._config()
        else:
            self._info()
