# -*- coding: utf-8 -*-
from nicfit import command
from nicfit.console.ansi import Fg, Style
from pyfiglet import figlet_format
from sqlalchemy.exc import ProgrammingError, OperationalError
# FIXME: replace thise console utils with nicfit.console
from eyed3.utils.console import printError
from eyed3.utils.console import cprint, cformat
from .. import version
from ..core import Command
from ..orm import Track, Artist, Album, Meta, Tag, Library, NULL_LIB_ID

"""
TODO:
    - command line arg for selecting libary
"""


@command.register
class Info(Command):
    NAME = "info"
    HELP = "Show information about the database and configuration."

    def _run(self):
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

        cprint(figlet_format("``MishMash``", font="graffiti"), Fg.GREEN,
                styles=[Style.BRIGHT])

        _addOutput("Version", version)
        _addOutput("Database URL", self.config.db_url)

        try:
            meta = session.query(Meta).one()
        except (ProgrammingError, OperationalError) as ex:
            printError("\nError querying metadata. Database may not be "
                       "initialized: %s" % str(ex))
            return 1

        _addOutput("Database version", meta.version)
        _addOutput("Last sync", meta.last_sync or "Never")
        _addOutput("Configuration file ", self.args.config.filename or "None")
        _printOutput("%s : %s", _output, key_fg=Fg.BLUE)

        print("")
        for lib in session.query(Library)\
                          .filter(Library.id > NULL_LIB_ID).all():
            cprint("\n=== {} library ===".format(lib.name), Fg.YELLOW)
            _addOutput(None, None)
            for name, orm_type in [("tracks", Track), ("artists", Artist),
                                  ("albums", Album), ("tags", Tag),
                         ]:
                count = session.query(orm_type).filter_by(lib_id=lib.id)\
                               .count()

                _addOutput(str(count), name)
            _printOutput("%s music %s", _output)
