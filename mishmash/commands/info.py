import sys
from nicfit.console.ansi import Fg, Style
from pyfiglet import figlet_format
from sqlalchemy.exc import ProgrammingError, OperationalError
from .. import version
from ..core import Command
from ..util import safeDbUrl
from ..orm import Track, Artist, Album, Meta, Tag, Library

"""
TODO:
    - command line arg for selecting libary
"""


class DisplayList:
    def __init__(self):
        self._rows = []

    def add(self, key, val):
        self._rows.append(tuple((key, val)))

    def print(self, _format, clear=False, **kwargs):
        k_width = max([len(k) for k, v in self._rows if k])
        for k, v in self._rows:
            if k:
                print(_format.format(k=k.ljust(k_width), v=v, **kwargs))

        if clear:
            self.clear()

    def clear(self):
        self._rows.clear()


@Command.register
class Info(Command):
    NAME = "info"
    HELP = "Show information about the database and configuration."
    _library_arg_nargs = "*"

    def _initArgParser(self, parser):
        super()._initArgParser(parser)
        parser.add_argument("--artists", dest="show_artists",
                            action="store_true",
                            help="List all artists, per library.")

    def lib_query(self, OrgType, lib):
        if isinstance(lib, int):
            lid = lib
        else:
            lid = lib.id
        return self.db_session.query(OrgType).filter_by(lib_id=lid)

    def _displayMetaInfo(self):
        display_list = DisplayList()

        def mkkey(k):
            return Style.bright(Fg.blue(str(k)))

        def mkval(v):
            return str(v)

        display_list.add(mkkey("Version"), mkval(version))
        display_list.add(mkkey("Database URL"),
                         mkval(safeDbUrl(self.config.db_url)))
        try:
            meta = self.db_session.query(Meta).one()
        except (ProgrammingError, OperationalError) as ex:
            print("\nError querying metadata. Database may not be "
                  "initialized: %s" % str(ex), file=sys.stderr)
            return 1

        display_list.add(mkkey("Database version"), mkval(meta.version))
        display_list.add(mkkey("Last sync"), mkval(meta.last_sync or "Never"))
        display_list.add(mkkey("Configuration files "),
                         mkval(", ".join(self.args.config.input_filenames)))
        display_list.print("{k} {delim} {v}", delim=Style.bright(":"))

    def _displayLibraryInfo(self, lib):
        def mkkey(k):
            return Style.bright(str(k))

        display_list = DisplayList()
        for name, orm_type in [("tracks", Track), ("artists", Artist),
                               ("albums", Album), ("tags", Tag),
                              ]:
            count = self.lib_query(orm_type, lib).count()
            display_list.add(mkkey(count), name)

        display_list.print("{k} music {v}", clear=True)

    def _displayArtists(self, lib):
        for a in self.lib_query(Artist, lib).order_by(Artist.sort_name).all():
            print(a.name)

    def _run(self):
        logo = figlet_format("``MishMash``", font="graffiti")
        print(Fg.green(logo, Style.BRIGHT))

        self._displayMetaInfo()

        for lib in Library.iterall(self.db_session, names=self.args.libs):
            if self.args.show_artists:
                print(Fg.green(f"\n=== {lib.name} library artists ==="))
                self._displayArtists(lib)
            else:
                print(Fg.green(f"\n=== {lib.name} library ==="))
                self._displayLibraryInfo(lib)
