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
from collections import OrderedDict
from .. import database


class Command(object):
    '''Base class for all mishmash commands.'''

    _all_commands = OrderedDict()

    # FIXME: why is the default subparsers=None? it is obviously required.
    def __init__(self, help, subparsers=None):
        self.subparsers = subparsers
        self.parser = self.subparsers.add_parser(self.NAME, help=help)
        self.parser.set_defaults(func=self.run)

    def run(self, args, config):
        self.args = args
        self.config = config
        self.db_engine, Session = database.init(self.config)

        self.db_session = Session()
        try:
            retval = self._run()
            self.db_session.commit()
        except:
            self.db_session.rollback()
            raise
        finally:
            self.db_session.close()

        return retval

    def _run(self):
        raise NotImplementedError("Must implement a _run function")

    @staticmethod
    def initAll(subparsers):
        for cmd in Command._all_commands.values():
            cmd(subparsers)


def register(CommandSubClass):
    '''A class decorator for Command classes to register in the default
    set.'''
    # Gotta mae the command name a class var
    Command._all_commands[CommandSubClass.NAME] = CommandSubClass
    return CommandSubClass
