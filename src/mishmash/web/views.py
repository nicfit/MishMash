from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from ..info import NAME, VERSION
_vars = {"project_name": NAME,
         "project_version": VERSION,
        }

from .models import DBSession
from ..orm import Artist, Album, VARIOUS_ARTISTS_NAME
from .. import database
from .. import util


class ResponseDict(dict):
    def __init__(self, *args, **kwargs):
        super(ResponseDict, self).__init__(*args, **kwargs)
        self.update(_vars)


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
    SINGLE_TYPE = "Single"

    session = request.DBSession()
    artists = session.query(Artist)\
                     .filter_by(name=request.matchdict["name"]).all()

    if len(artists) == 1:
        artist = artists[0]
        albums = util.sortAlbums(artist.albums)
        all_tabs = Album.ALBUM_TYPES + [SINGLE_TYPE]

        active_albums = []
        active_singles = []
        active_tab = request.GET.get("album_tab", None)
        if not active_tab:
            # No album type was requested, try to pick a smart one.
            for active_tab in all_tabs:
                if active_tab != SINGLE_TYPE:
                    active_albums = artist.getAlbumsByType(active_tab)
                else:
                    active_singles = artist.getTrackSingles()
                if active_albums or active_singles:
                    break
        else:
            if active_tab != SINGLE_TYPE:
                active_albums = artist.getAlbumsByType(active_tab)
            else:
                active_singles = artist.getTrackSingles()

        tabs = []
        for name in all_tabs:
            t = (name, "%ss" % name, active_tab == name)
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

