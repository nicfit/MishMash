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
import random
from pyramid_layout.panel import panel_config
from ..__about__ import __version__, __years__, __project_name__
from .. import orm


@panel_config(name='navbar',
              renderer='mishmash.web:templates/panels/navbar.pt')
def navbar(context, request):
    def nav_item(name, url):
        active = request.current_route_url() == url
        item = dict(name=name,
                    url=url,
                    active=active,
                   )
        return item

    nav = [nav_item('Artists', request.route_url('all_artists')),
           nav_item('New Music', request.route_url("new_music")),
          ]
    return {'title': 'Mishmash',
            'nav': nav,
           }


@panel_config(name='footer')
def footer(context, request):
    return ("<footer>"
            "<p align='right'>%(NAME)s %(VERSION)s &copy; %(YEARS)s"
            "</footer>" %
            dict(NAME=__project__name__,
                 VERSION=__version__,
                 YEARS=__years__))


@panel_config(name='album_cover')
def album_cover(context, request, album, size=None, link=False):
    front_covers = [img for img in album.images
                        if img.type == orm.Image.FRONT_COVER_TYPE]
    cover_id = random.choice(front_covers).id if front_covers else "default"
    cover_url = request.route_url("images.covers", id=cover_id)
    width = str(size or "100%")
    height = str(size or "100%")

    panel = (
        u"<img class='shadow' width='%s' height='%s' src='%s' title='%s'/>" %
        (width, height, cover_url, "%s - %s" % (album.artist.name, album.title))
    )

    if link:
        panel = u"<a href='%s'>%s</a>" % \
                (request.route_url('album', id=album.id), panel)

    return panel
