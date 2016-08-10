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
import os

from eyed3.core import VARIOUS_TYPE
from eyed3.utils.prompt import prompt
from eyed3.utils.console import (Style, Fore as fg)

from ..console import promptArtist, selectArtist
from ..orm import Artist
from ..util import normalizeCountry, commonDirectoryPrefix, mostCommonItem
from . import command

'''Metadata management commands.'''


@command.register
class SplitArtists(command.Command):
    NAME = "split-artists"

    def __init__(self, subparsers=None):
        super(SplitArtists, self).__init__(
                "Split a single artist name into N distinct artists.",
                subparsers)
        self.parser.add_argument("artist",
                                 help="The name of the artist to split.")

    def _displayArtistMusic(self, artist, albums, singles):
        if albums:
            print(u"%d albums by %s:" % (len(albums),
                                         Style.bright(fg.blue(artist.name))))
            for alb in albums:
                print(u"%s %s" % (str(alb.getBestDate()).center(17),
                                  alb.title))

        if singles:
            print(u"%d single tracks by %s" %
                  (len(singles), Style.bright(fg.blue(artist.name))))
            for s in singles:
                print(u"\t%s" % (s.title))

    def _run(self):
        session = self.db_session

        artists = session.query(Artist)\
                         .filter(Artist.name == self.args.artist).all()
        if not artists:
            print(u"Artist not found: %s" % self.args.artist)
            return 1
        elif len(artists) > 1:
            artist = selectArtist(fg.blue("Select which '%s' to split...") %
                                  artists[0].name,
                                  choices=artists, allow_create=False)
        else:
            artist = artists[0]

        # Albums by artist
        albums = list(artist.albums) + artist.getAlbumsByType(VARIOUS_TYPE)
        # Singles by artist and compilations the artist appears on
        singles = artist.getTrackSingles()

        if len(albums) < 2 and len(singles) < 2:
            print("%d albums and %d singles found for '%s', nothing to do." %
                    (len(albums), len(singles), artist.name))
            return 0

        self._displayArtistMusic(artist, albums, singles)

        def _validN(_n):
            return _n > 1 and _n <= len(albums)
        n = prompt("\nEnter the number of distinct artists", type_=int,
                   validate=_validN)
        new_artists = []
        for i in range(1, n + 1):
            print(Style.bright(u"\n%s #%d") % (fg.blue(artist.name), i))

            # Reuse original artist for first
            a = artist if i == 1 else Artist(name=artist.name,
                                             date_added=artist.date_added)
            a.origin_city = prompt("   City", required=False)
            a.origin_state = prompt("   State", required=False)
            a.origin_country = prompt("   Country", required=False,
                                      type_=normalizeCountry)
            import ipdb; ipdb.set_trace()

            new_artists.append(a)

        if not Artist.checkUnique(new_artists):
            print(fg.red("Artists must be unique."))
            return 1

        for a in new_artists:
            session.add(a)

        # New Artist objects need IDs
        session.flush()

        print(Style.bright("\nAssign albums to the correct artist."))
        for i, a in enumerate(new_artists):
            print("Enter %s%d%s for %s from %s%s%s" %
                  (Style.BRIGHT, i + 1, Style.RESET_BRIGHT,
                  a.name,
                  Style.BRIGHT, a.origin(country_code="iso3c",
                                         title_case=False),
                  Style.RESET_BRIGHT))

        # prompt for correct artists
        def _promptForArtist(_text):
            a = prompt(_text, type_=int,
                       choices=range(1, len(new_artists) + 1))
            return new_artists[a - 1]

        print("")
        for alb in albums:
            # Get some of the path to help the decision
            path = commonDirectoryPrefix(*[t.path for t in alb.tracks])
            path = os.path.join(*path.split(os.sep)[-2:])

            a = _promptForArtist("%s (%s)" % (alb.title, path))
            if alb.type != "various":
                alb.artist_id = a.id
            for track in alb.tracks:
                if track.artist_id == artist.id:
                    track.artist_id = a.id

        print("")
        for track in singles:
            a = _promptForArtist(track.title)
            track.artist_id = a.id

        session.flush()



@command.register
class MergeArtists(command.Command):
    NAME = "merge-artists"

    def __init__(self, subparsers=None):
        super(MergeArtists, self).__init__(
                "Merge two or more artists into a single artist.",
                subparsers)
        self.parser.add_argument("artists", nargs="+",
                                 help="The artist names to merge.")

    def _run(self):
        session = self.db_session

        merge_list = []
        for artist_arg in self.args.artists:
            artists = session.query(Artist)\
                             .filter(Artist.name == artist_arg).all()
            if len(artists) == 1:
                merge_list.append(artists[0])
            elif len(artists) > 1:
                merge_list += selectArtist(
                        fg.blue("Select the artists to merge..."),
                        multiselect=True, choices=artists)

        if len(merge_list) > 1:
            # Reuse lowest id
            artist_ids = {a.id: a for a in merge_list}
            min_id = min(*artist_ids.keys())
            artist = artist_ids[min_id]

            mc = mostCommonItem
            new_artist = promptArtist(
                    "Merging %d artists into new artist..." % len(merge_list),
                    default_name=mc([a.name for a in merge_list]),
                    default_city=mc([a.origin_city for a in merge_list]),
                    default_state=mc([a.origin_state for a in merge_list]),
                    default_country=mc([a.origin_country for a in merge_list]),
                    artist=artist)
        else:
            print("Nothing to do, %s" %
                    ("artist not found" if not len(merge_list)
                                        else "only one artist found"))
            return 1

        assert(new_artist in merge_list)

        for artist in merge_list:
            if artist is new_artist:
                continue

            with session.no_autoflush:
                for alb in list(artist.albums):
                    # FIXME: use constant
                    if alb.type != "various":
                        alb.artist_id = new_artist.id
                        artist.albums.remove(alb)
                        with session.no_autoflush:
                            new_artist.albums.append(alb)

                    for track in alb.tracks:
                        if track.artist_id == artist.id:
                            # gotta check in case alb is type various
                            track.artist_id = new_artist.id

                for track in artist.getTrackSingles():
                    track.artist_id = new_artist.id

            # flush to get new artist ids in sync before delete, otherwise
            # cascade happens.
            session.flush()
            session.delete(artist)

            session.flush()

        # FIXME: prompt for whether the tags should be updated with the new
        # name if it is new.
