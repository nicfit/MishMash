import os
import random
from hashlib import sha1
from gettext import gettext as _

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPNotFound, HTTPNotModified

from sqlalchemy import desc

from eyed3.utils import formatTime
from eyed3.core import (LP_TYPE, EP_TYPE, COMP_TYPE, VARIOUS_TYPE, LIVE_TYPE,
                        DEMO_TYPE, SINGLE_TYPE, ALBUM_TYPE_IDS)

from ..__about__ import __project_name__ as PROJECT_NAME
from ..__about__ import __version__ as VERSION

from .. import database
from .. import util
from ..orm import Artist, Album, Image, VARIOUS_ARTISTS_NAME, VARIOUS_ARTISTS_ID

_vars = {"project_name": PROJECT_NAME,
         "project_version": VERSION,
        }


class ResponseDict(dict):
    def __init__(self, *args, **kwargs):
        super(ResponseDict, self).__init__(*args, **kwargs)
        self.update(_vars)


# Not in eyeD3
ALL_TYPE = "All"
TYPE_DISPLAY_NAMES = {ALL_TYPE: _(ALL_TYPE),
                      LP_TYPE: _("LPs"),
                      EP_TYPE: _("EPs"),
                      COMP_TYPE: _("Compilations"),
                      VARIOUS_TYPE: VARIOUS_ARTISTS_NAME,
                      LIVE_TYPE: _("Live"),
                      DEMO_TYPE: _("Demos"),
                      SINGLE_TYPE: _("Singles"),
                     }
TYPE_DISPLAY_NAMES[ALL_TYPE] = _(ALL_TYPE)


@view_config(route_name="home", renderer="templates/home.pt",
             layout="main-layout")
def home_view(request):
    return ResponseDict()


@view_config(route_name="all_artists", renderer="templates/artists.pt",
             layout="main-layout")
def allArtistsView(request):
    NUM_COLS = 2
    NUMBER = "#"
    OTHER = "Other"
    buckets = {}   # buckets['A'] = count, etc.
    artist_dict = {}

    def _whichBucket(name):
        first_l = name[0].upper()
        if not first_l.isalpha():
            first_l = NUMBER if first_l.isnumeric() else OTHER
        if first_l not in buckets:
            buckets[first_l] = 0
        buckets[first_l] += 1
        return first_l

    count = 0
    active_types = _getActiveAlbumTypes(request.params)
    artist_types = {}
    session = request.DBSession
    for artist in session.query(Artist)\
                         .order_by(Artist.sort_name).all():

        types = set([alb.type for alb in artist.albums])
        for t in types:
            if t not in artist_types:
                artist_types[t] = {
                    "active": t in active_types,
                    "display_name": TYPE_DISPLAY_NAMES[t],
                }

        if not active_types.intersection(types):
            continue

        count += 1

        bucket = _whichBucket(artist.sort_name)
        if bucket not in artist_dict:
            artist_dict[bucket] = []

        if artist_dict[bucket]:
            # Adding show_origin member to the instance here. True for
            # dup artists, false otherwise.
            if artist_dict[bucket][-1].name == artist.name:
                artist_dict[bucket][-1].show_origin = True
                artist.show_origin = True
            else:
                artist.show_origin = False
        else:
            artist.show_origin = False

        artist_dict[bucket].append(artist)

    keys = list(buckets.keys())
    keys.sort()
    if OTHER in keys:
        keys.remove(OTHER)
        keys.append(OTHER)

    # Build column based on keys and counts
    col_cnt, col_curr = 0, 0
    key_cols = []   # key_cols[0] = [k1, k2, ...], key_cols[1] = [k10, ...]
    key_cols.append([])
    num_per_col = round(count / NUM_COLS)
    for k in keys:
        col_cnt += buckets[k]
        if col_cnt >= num_per_col:
            key_cols.append([])
            col_curr += 1
            col_cnt = 0

        key_cols[col_curr].append(k)

    return ResponseDict(artist_keys=keys, artist_dict=artist_dict, artist_types=artist_types,
                        artist_count=count, key_columns=key_cols)


@view_config(route_name="artist", renderer="templates/artist.pt",
             layout="main-layout")
def artistView(request):
    artist_id = int(request.matchdict["id"])
    session = request.DBSession

    artist = session.query(Artist).filter_by(id=artist_id).first()
    if not artist:
        raise HTTPNotFound()

    def _filterByType(typ, artist, albums):
        if typ == SINGLE_TYPE:
            return artist.getTrackSingles()
        elif typ == ALL_TYPE:
            return albums
        else:
            return artist.getAlbumsByType(typ)

    albums = list(artist.albums)
    all_tabs = [ALL_TYPE] + ALBUM_TYPE_IDS

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
        # XXX active_singles = util.sortByDate(active_singles)
        pass

    for a in active_albums:
        covers = [img for img in a.images
                        if img.type == Image.FRONT_COVER_TYPE]
        a.cover = random.choice(covers) if covers else None

    tabs = {}
    if artist.id != VARIOUS_ARTISTS_ID:
        for name in all_tabs:
            t = dict(name=name, display_name=TYPE_DISPLAY_NAMES[name], active=active_tab == name,
                     has_items=bool(len(_filterByType(name, artist, albums))))
            if name in tabs:
                raise ValueError("Duplicate album type found: " + name)
            tabs[name] = t

        if len([t for t in tabs.values() if t["has_items"]]) == 2:
            # If all we have is "All" and another type, lose "All"
            tabs[ALL_TYPE]["has_items"] = False

    return ResponseDict(artist=artist,
                        active_tab=active_tab,
                        active_albums=active_albums,
                        active_singles=active_singles,
                        tabs=tabs,
                       )


@view_config(route_name="images.covers")
def covers(request):
    return _imageView(request, default_resp=Response(content_type="image/png",
                                                     body=DEFAULT_COVER_DATA))


@view_config(route_name="images.artist")
def artist_images(request):
    return _imageView(request)


with open(os.path.join(os.path.dirname(__file__),
                       "static",
                       "record150.png"), "rb") as _cover_fp:
    DEFAULT_COVER_DATA = _cover_fp.read()
del _cover_fp


@view_config(route_name="new_music", renderer="templates/new_music.pt",
             layout="main-layout")
def newMusicView(request):
    from math import ceil
    session = request.DBSession
    albums = session.query(Album).order_by(desc("date_added")).limit(25).all()
    return ResponseDict(albums=albums, ceil=ceil)


@view_config(route_name="album", renderer="templates/album.pt",
             layout="main-layout")
def albumView(request):
    album_id = int(request.matchdict["id"])
    session = request.DBSession

    album = session.query(Album).filter_by(id=album_id).first()
    if not album:
        raise HTTPNotFound()
    return ResponseDict(album=album,
                        formatTime=formatTime,
                       )


@view_config(route_name="search", renderer="templates/search_results.pt",
             layout="main-layout")
def searchView(request):
    query = request.POST["q"]
    results = database.search(request.DBSession, query)
    return ResponseDict(**results)


@view_config(route_name="all_albums", renderer="templates/albums.pt",
             layout="main-layout")
def allAlbumsView(request):
    album_dict = {}
    album_types = {}

    if ("filter-form" in request.params and request.params.get("filter-form") == "true"
            and not request.params.getall("type")):
        # Form submit with no filters checks, this is not the default /albums
        active_types = set()
    else:
        active_types = _getActiveAlbumTypes(request.params)

    session = request.DBSession
    for album in session.query(Album)\
                        .order_by(Album.original_release_date).all():

        if album.type not in album_types:
            album_types[album.type] = {
                "active": album.type in active_types,
                "display_name": TYPE_DISPLAY_NAMES[album.type],
            }

        if not album_types[album.type]["active"]:
            continue

        d = album.getBestDate()
        bucket = d.year // 10 * 10 if d else 0
        if bucket not in album_dict:
            album_dict[bucket] = []

        album_dict[bucket].append(album)

    buckets = list(album_dict.keys())
    buckets.sort()

    return ResponseDict(album_decades=buckets, album_dict=album_dict, album_types=album_types)


def _imageView(request, default_resp=None):
    iid = request.matchdict["id"]

    if iid == "default" and default_resp:
        resp = default_resp
    else:
        session = request.DBSession
        image = session.query(Image).filter(Image.id == int(iid)).first()
        if not image:
            raise HTTPNotFound()
        resp = Response(content_type=image.mime_type, body=image.data)

    hash = sha1()
    hash.update(resp.body)
    etag = hash.hexdigest()
    if "If-None-Match" in request.headers and request.headers["If-None-Match"] == etag:
        raise HTTPNotModified()

    resp.headers["Cache-Control"] = "max-age=3600"
    resp.headers["ETag"] = etag

    return resp


def _getActiveAlbumTypes(params):
    inc_types = set([p for p in params.getall("type") if p[0] != '!'])
    exc_types = set([p[1:] for p in params.getall("type") if p[0] == '!'])
    active_types = set(ALBUM_TYPE_IDS).difference(exc_types)
    if inc_types:
        active_types = active_types.intersection(inc_types)
    return active_types
