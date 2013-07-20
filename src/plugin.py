# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2012  Travis Shirk <travis@pobox.com>
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

from sqlalchemy.sql.expression import func


class MishMashPlugin(LoaderPlugin):
    '''DEPRECATED: Leaving this only until the code below migrates.'''


        if self.args.show_artists:
            banner = None
            for artist in session.query(Artist)\
                                 .order_by(Artist.sort_name).all():
                if banner != artist.sort_name[0]:
                    banner = artist.sort_name[0]
                    printMsg(u"\n== %s ==" % banner)
                printMsg(u"\t%s" % artist.sort_name)

        elif self.args.search:
            print("\nSearch:")
            s = self.args.search

            print("Artists:")
            for artist in session.query(Artist).filter(
                    Artist.name.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d)" % (artist.name, artist.id))

            print("Albums:")
            for album in session.query(Album).filter(
                    Album.title.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d) (artist: %s)" % (album.title, album.id,
                                                       album.artist.name))

            print("Tracks:")
            for track in session.query(Track).filter(
                    Track.title.ilike(u"%%%s%%" % s)).all():
                print(u"\t%s (id: %d) (artist: %s) (album: %s)" %
                      (track.title, track.id,
                       track.artist.name,
                       track.album.title if track.album else None))
        elif self.args.random:
            for track in session.query(Track)\
                                .order_by(func.random())\
                                .limit(self.args.random).all():
                print(track.path)
        elif self.args.listing:
            if self.args.listing == "artists":
                banner = None
                for artist in session.query(Artist)\
                                     .order_by(Artist.sort_name).all():
                    if banner != artist.sort_name[0]:
                        banner = artist.sort_name[0]
                        printMsg(u"\n== %s ==" % banner)
                    printMsg(u"\t%s" % artist.sort_name)
