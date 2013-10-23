import os
import random

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound

from sqlalchemy.exc import DBAPIError

from eyed3.core import ALBUM_TYPE_IDS
from eyed3.core import (LP_TYPE, EP_TYPE, COMP_TYPE, VARIOUS_TYPE, LIVE_TYPE,
                        DEMO_TYPE)

from ..info import NAME, VERSION
_vars = {"project_name": NAME,
         "project_version": VERSION,
        }

from .models import DBSession
from ..orm import Artist, Album, Image, VARIOUS_ARTISTS_NAME
from .. import database
from .. import util


class ResponseDict(dict):
    def __init__(self, *args, **kwargs):
        super(ResponseDict, self).__init__(*args, **kwargs)
        self.update(_vars)


TYPE_DISPLAY_NAMES = {LP_TYPE: "LPs",
                      EP_TYPE: "EPs",
                      COMP_TYPE: "Compilations",
                      VARIOUS_TYPE: "Various Artists",
                      LIVE_TYPE: "Live",
                      DEMO_TYPE: "Demos",
                     }
# Not in eyeD3
SINGLE_TYPE = "Single"
ALL_TYPE = "All"
TYPE_DISPLAY_NAMES[SINGLE_TYPE] = "Singles"
TYPE_DISPLAY_NAMES[ALL_TYPE] = "All"


@view_config(route_name="home", renderer="templates/home.pt",
             layout="main-layout")
def home_view(request):
    return ResponseDict()

@view_config(route_name="artists", renderer="templates/artists.pt",
             layout="main-layout")
def allArtistsView(request):
    NUMBER = u"#"
    OTHER = u"Other"

    buckets = set()
    artist_dict = {}

    def _bucket(name):
        l = name[0].upper()
        if not l.isalpha():
            l = NUMBER if l.isnumeric() else OTHER
        buckets.add(l)
        return l

    session = request.DBSession()
    for artist in session.query(Artist)\
                         .order_by(Artist.sort_name).all():

        bucket = _bucket(artist.sort_name)
        if bucket not in artist_dict:
            artist_dict[bucket] = []
        artist_dict[bucket].append(artist)

    buckets = list(buckets)
    buckets.sort()
    if OTHER in buckets:
        buckets.remove(OTHER)
        buckets.append(OTHER)

    return ResponseDict(artist_keys=buckets,
                        artist_dict=artist_dict)


@view_config(route_name="single_artist", renderer="templates/artist.pt",
             layout="main-layout")
def singleArtistView(request):
    session = request.DBSession()
    artists = session.query(Artist)\
                     .filter_by(name=request.matchdict["name"]).all()

    def _filterByType(typ, artist, albums):
        if typ == SINGLE_TYPE:
            return artist.getTrackSingles()
        elif typ == ALL_TYPE:
            return albums
        else:
            return artist.getAlbumsByType(typ)

    if len(artists) == 1:
        artist = artists[0]
        albums = list(artist.albums)
        all_tabs = ALBUM_TYPE_IDS + [SINGLE_TYPE, ALL_TYPE]

        active_albums = []
        active_singles = []
        active_tab = request.GET.get("album_tab", None)
        if not active_tab:
            # No album type was requested, try to pick a smart one.
            for active_tab in all_tabs:
                active_albums = _filterByType(active_tab, artist, albums)
                if active_albums:
                    break
        else:
            active_albums = _filterByType(active_tab, artist, albums)

        if active_tab == SINGLE_TYPE:
            active_singles = active_albums
            active_albums = []

        if active_albums:
            active_albums = util.sortByDate(active_albums,
                                            active_tab == LIVE_TYPE)
        else:
            # Unlike tags, the orm.Track does not have dates so not sorting :/
            #active_singles = util.sortByDate(active_singles)
            pass

        for a in active_albums:
            covers = [img for img in a.images
                            if img.type == Image.FRONT_COVER_TYPE]
            a.cover = random.choice(covers) if covers else None

        tabs = []
        for name in all_tabs:
            t = (name, TYPE_DISPLAY_NAMES[name], active_tab == name)
            tabs.append(t)
        return ResponseDict(artist=artists[0],
                            active_tab=active_tab,
                            active_albums=active_albums,
                            active_singles=active_singles,
                            tabs=tabs,
                            )
    elif len(artists) > 1:
        raise NotImplementedError("TODO")
    else:
        raise NotImplementedError("TODO")


@view_config(route_name="search", renderer="templates/search_results.pt",
             layout="main-layout")
def searchResultsView(request):
    return ResponseDict()


@view_config(route_name="images.covers")
def covers(request):
    iid = request.matchdict["id"]

    if iid == "default":
        return Response(content_type="image/png", body=DEFAULT_COVER_DATA)
    else:
        session = request.DBSession()
        image = session.query(Image).filter(Image.id == int(iid)).first()
        if not image:
            raise HTTPNotFound()
        return Response(content_type=image.mime_type.encode("latin1"),
                        body=image.data)

DEFAULT_COVER_DATA = open(os.path.join(os.path.dirname(__file__), "static",
                                       "record150.png"), "rb").read()
