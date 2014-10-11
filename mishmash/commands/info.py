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
from sqlalchemy.exc import ProgrammingError, OperationalError
from eyed3.utils.console import printError
from ..orm import Track, Artist, Album, Meta, Label
from . import command


@command.register
class Info(command.Command):
    NAME = "info"

    def __init__(self, subparsers=None):
        super(Info, self).__init__("Show information about the database or "
                                   "configuration.", subparsers)
        self.parser.add_argument("-C", "--show-config", action="store_true",
                                 help="Display current configurion.")

    def _run(self):
        if self.args.show_config:
            self.config.write(sys.stdout)
            self.config.write(open("config.ini", "w"))
        else:
            session = self.db_session

            print("\nDatabase:")
            print("\tURL: %s" % self.config.db_url)
            try:
                meta = session.query(Meta).one()
            except (ProgrammingError, OperationalError) as ex:
                printError("\nError querying metadata. Database may not be "
                           "initialized: %s" % str(ex))
                return 1

            print("\tVersion: %s" % meta.version)
            print("\tLast Sync: %s" % meta.last_sync)

            print("\nMusic:")
            print("\t%d tracks" % session.query(Track).count())
            print("\t%d artists" % session.query(Artist).count())
            print("\t%d albums" % session.query(Album).count())
            print("\t%d labels" % session.query(Label).count())
