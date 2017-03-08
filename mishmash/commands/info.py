# -*- coding: utf-8 -*-
from nicfit import command
from nicfit.console.ansi import Fg, Style
from pyfiglet import figlet_format
from sqlalchemy.exc import ProgrammingError, OperationalError
# FIXME: replace thise console utils with nicfit.console
from eyed3.utils.console import printError
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

        def _addOutput(k, v):
            _output.append(tuple((k, v)))

        def _printOutput(_format, _olist):
            k_width = max([len(k) for k, v in _olist if k])
            for k, v in _olist:
                if k:
                    print(_format.format(k=k.ljust(k_width), v=v))
            _olist.clear()

        logo = figlet_format("``MishMash``", font="graffiti")
        print(Fg.green(logo, Style.BRIGHT))

        def mkkey(k):
            return Style.bright(Fg.blue(str(k)))

        def mkval(v):
            return Style.bright(Fg.blue(str(v)))

        _addOutput(mkkey("Version"), mkval(version))
        _addOutput(mkkey("Database URL"), mkval(self.config.db_url))

        try:
            meta = session.query(Meta).one()
        except (ProgrammingError, OperationalError) as ex:
            printError("\nError querying metadata. Database may not be "
                       "initialized: %s" % str(ex))
            return 1

        _addOutput(mkkey("Database version"), mkval(meta.version))
        _addOutput(mkkey("Last sync"), mkval(meta.last_sync or "Never"))
        _addOutput(mkkey("Configuration file "),
                   mkval(self.args.config.filename or "None"))
        _printOutput("{k} : {v}", _output)

        def mkkey(k):
            return Style.bright(str(k))

        print("")
        for lib in session.query(Library)\
                          .filter(Library.id > NULL_LIB_ID).all():
            print(Fg.yellow("\n=== {} library ===").format(lib.name))
            _addOutput(None, None)
            for name, orm_type in [("tracks", Track), ("artists", Artist),
                                  ("albums", Album), ("tags", Tag),
                         ]:
                count = session.query(orm_type).filter_by(lib_id=lib.id)\
                               .count()

                _addOutput(mkkey(count), name)
            _printOutput("{k} music {v}", _output)
