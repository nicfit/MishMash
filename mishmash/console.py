# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2013-2014  Travis Shirk <travis@pobox.com>
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
from eyed3.utils.prompt import prompt, parseIntList
from eyed3.utils.console import Fore as fg
from .orm import Artist


def selectArtist(heading, choices=None, multiselect=False, allow_create=True):
    color = fg.green
    artist = None
    name = None

    if heading:
        print(heading)

    while artist is None:
        if choices:
            name = choices[0].name
            for menu_num, a in enumerate(choices):
                print("   %d) %s" % (menu_num + 1, a.origin()))
            menu_num += 1

            if not multiselect:
                if allow_create:
                    menu_num += 1
                    print("   %d) Enter a new artist" % menu_num)

                choice = prompt("Which artist", type_=int,
                                choices=range(1, menu_num + 1))
                choice -= 1
                if choice < len(choices):
                    artist = choices[choice]
                # Otherwise fall through to select artist below
            else:
                def _validate(_resp):
                    try:
                        _ints = [_i for _i in parseIntList(_resp)
                                    if _i in range(1, menu_num + 1)]
                        return bool(_ints)
                    except:
                        return False

                resp = prompt(color("Choose one or more artists"),
                              validate=_validate)
                artists = []
                for choice in [i - 1 for i in parseIntList(resp)]:
                    artists.append(choices[choice])
                # XXX: blech, returning a list here and a single value below
                return artists

        if artist is None:
            artist = promptArtist(None, name=name)
            if choices:
                if not Artist.checkUnique(choices + [artist]):
                    print(fg.red("Artist entered is not unique, try again..."))
                    artist = None

    assert(artist)
    return artist


def promptArtist(text, name=None, default_name=None, default_city=None,
                 default_state=None, default_country=None, artist=None):
    if text:
        print(text)

    if name is None:
        name = prompt(fg.green("Artist name"), default=default_name)

    origin = {}
    for o in ("city", "state", "country"):
        origin["origin_%s" % o] = prompt("   %s" % fg.green(o.title()),
                                         default=locals()["default_%s" % o],
                                         required=False)

    if not artist:
        artist = Artist(name=name, **origin)
    else:
        artist.name = name
        for o in origin:
            setattr(artist, o, origin[o])
    return artist
