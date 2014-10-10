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
import logging
import warnings
import logging.config

from sqlalchemy import exc as sql_exceptions

import eyed3
eyed3.require("0.8")

from eyed3.utils.console import AnsiCodes
from eyed3.utils.console import Fore as fg
from eyed3.utils.prompt import PromptExit

from .database import MissingSchemaException
from .log import log, initLogging
from .commands import makeCmdLineParser
from . import config
from . import __release__


def _pErr(subject, msg):
    print(fg.red(subject) + ": %s" % str(msg))


def main():
    parser = makeCmdLineParser()
    parser.add_argument("--pdb", action="store_true", dest="debug_pdb",
                        help="Drop into 'pdb' when errors occur.")

    args = parser.parse_args()
    if args.debug_pdb:
        # The import of ipdb MUST be limited to explicit --pdb option
        # (what follows was at module scope prior) because of
        # https://github.com/gotcha/ipdb/issues/48. Which --pdb is
        # used with commands where stdout is captured you will bet extra
        # leading bytes.
        try:
            import ipdb as pdb
        except ImportError:
            import pdb
        def _pdb(args):
            e, m, tb = sys.exc_info()
            pdb.post_mortem(tb)

    app_config = config.load(args.config)
    logging.config.fileConfig(app_config)

    AnsiCodes.init(True)

    try:
        # Run command
        retval = args.func(args, app_config) or 0
    except (KeyboardInterrupt, PromptExit) as ex:
        # PromptExit raised when CTRL+D during prompt, or prompts disabled
        retval = 0
    except (sql_exceptions.ArgumentError,
            sql_exceptions.OperationalError) as ex:
        _pErr("Database error", ex)
        _pdb(args)
        retval = 1
    except MissingSchemaException as ex:
        _pErr("Schema error",
              "The table%s '%s' %s missing from the database schema." %
                 ('s' if len(ex.tables) > 1 else '',
                  ", ".join([str(t) for t in ex.tables]),
                  "are" if len(ex.tables) > 1 else "is")
             )
        retval = 1
    except Exception as ex:
        log.exception(ex)
        _pErr(ex.__class__.__name__, str(ex))
        _pdb(args)
        retval = 2

    return retval


if __name__ == "__main__":
    sys.exit(main())
