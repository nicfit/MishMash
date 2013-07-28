# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2013  Travis Shirk <travis@pobox.com>
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
from __future__ import print_function

import os
import sys
import getpass
from datetime import datetime

import eyed3
eyed3.require("0.7.4")

import eyed3.main
from eyed3.utils.cli import printError, printMsg, printWarning

from .database import MissingSchemaException
from .log import log, setupLogging
from .commands import makeCmdLineParser


def main():
    setupLogging()
    parser = makeCmdLineParser()

    # Run command
    args = parser.parse_args()
    try:
        retval = args.func(args) or 0
    except MissingSchemaException as ex:
        printError("Schema error:")
        printMsg("The table%s '%s' %s missing from the database schema." %
                 ('s' if len(ex.tables) > 1 else '',
                  ", ".join(ex.tables),
                  "are" if len(ex.tables) > 1 else "is"))
        retval = 1
    except Exception as ex:
        log.exception(ex)
        printError("%s: %s" % (ex.__class__.__name__, str(ex)))
        retval = 2

    return retval


if __name__ == "__main__":
    sys.exit(main())
