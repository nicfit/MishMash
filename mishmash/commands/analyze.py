import os
from hashlib import md5

import sqlalchemy as sa
from eyed3.core import VARIOUS_TYPE
from eyed3.utils.prompt import prompt, choicePrompt
from nicfit.console.ansi import Style, Fg

from ..orm import Artist, Library, Image, IMAGE_TABLES
from ..core import Command
from ..console import promptArtist, selectArtist
from ..util import normalizeCountry, commonDirectoryPrefix, mostCommonItem


@Command.register
class Analyze(Command):
    NAME = "analyze"
    HELP = "Search and fix library anomalies"
    _library_arg_nargs = 1

    def _initArgParser(self, parser):
        super()._initArgParser(parser)

    def _run(self):
        lib = self.db_session.query(Library).filter(Library.name == self.args.lib).one()
        self._analyzeArtists(lib)

    def _analyzeArtists(self, lib):
        sess = self.db_session

        # Fix case
        seen_dups = set()
        for a in sess.query(Artist).filter(Artist.lib_id == lib.id).all():
            dups = sess.query(Artist).filter(sa.func.lower(Artist.name) == sa.func.lower(a.name))\
                                     .all()
            if len(dups) > 1 and dups[0].id not in seen_dups:
                seen_dups = seen_dups.union([artist.id for artist in dups])
                _fixDupArtists(dups, sess)


def _fixDupArtists(artists, session):
    print("\n")
    dup = prompt(f"{' vs. '.join([a.name for a in artists])}\nDuplicate artist? ", default=True)
    if dup:
        from ..mgmt import mergeArtists
        mergeArtists(artists, session)
