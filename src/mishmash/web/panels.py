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
from pyramid_layout.panel import panel_config
from .. import info

#from .layouts import Thing1, Thing2, LittleCat


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

    nav = [
        nav_item('Artists', request.route_url('artists')),
        nav_item('Search', request.route_url('search')),
        nav_item('eyeD3', "http://eyed3.nicfit.net/")
        ]
    return {
        'title': 'Mishmash',
        'nav': nav,
        }


@panel_config(name='footer')
def footer(context, request):
    return ("<p align='right'>%(NAME)s %(VERSION)s &copy; %(YEARS)s" %
            dict(NAME=info.NAME,
                 VERSION=info.VERSION,
                 YEARS=info.YEARS))


