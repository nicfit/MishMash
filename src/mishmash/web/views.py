from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from ..info import NAME, VERSION
_vars = {"project_name": NAME,
         "project_version": VERSION,
        }

from .models import DBSession
from ..orm import Artist
from .. import database
from .. import util


class ResponseDict(dict):
    def __init__(self, *args, **kwargs):
        super(ResponseDict, self).__init__(*args, **kwargs)
        self.update(_vars)


@view_config(route_name='home', renderer='templates/home.pt')
def home_view(request):
    return ResponseDict()

@view_config(route_name='artists', renderer='templates/artists.pt')
def allArtistsView(request):

    full_list = []
    curr_part = None
    partitioned_artists = {}

    session = request.DBSession()
    for artist in session.query(Artist)\
                         .order_by(Artist.sort_name).all():
        if curr_part != artist.sort_name[0]:
            curr_part = artist.sort_name[0]
            partitioned_artists[curr_part] = []

        partitioned_artists[curr_part].append(artist)
        full_list.append(artist)

    return ResponseDict(all_artists=full_list,
                        partitioned_artists=partitioned_artists)


@view_config(route_name='single_artist', renderer='templates/artist.pt')
def singleArtistView(request):
    session = request.DBSession()
    artists = session.query(Artist)\
                     .filter_by(name=request.matchdict["name"]).all()

    if len(artists) == 1:
        artist = artists[0]
        # FIXME: begin here
        albums = util.sortAlbums(artist.albums)
        return ResponseDict(artist=artists[0],
                            albums=albums)
    elif len(artists) > 1:
        raise NotImplementedError("TODO")
    else:
        raise NotImplementedError("TODO")


@view_config(route_name='search', renderer='templates/search_results.pt')
def searchResultsView(request):
    return ResponseDict()


@view_config(route_name='pyramid', renderer='templates/pyramid.pt')
def pyramid_info_view(request):
    conn_err_msg = """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_web_db" script
    to initialize your database tables.  Check your virtual
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""
    return {'project': 'mishmash'}

