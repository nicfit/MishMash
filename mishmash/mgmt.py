from .orm import VARIOUS_TYPE
from .util import mostCommonItem
from .console import promptArtist


def mergeArtists(artists, session):

    # Reuse lowest id
    artist_ids = {a.id: a for a in artists}
    min_id = min(*artist_ids.keys())

    artist = artist_ids[min_id]

    mc = mostCommonItem
    new_artist = promptArtist("Merging %d artists into new artist..." % len(artists),
                              default_name=mc([a.name for a in artists]),
                              default_city=mc([a.origin_city for a in artists]),
                              default_state=mc([a.origin_state for a in artists]),
                              default_country=mc([a.origin_country for a in artists]),
                              artist=artist)

    assert new_artist.lib_id == artist.lib_id
    assert (new_artist in artists)

    for artist in artists:
        if artist is new_artist:
            continue

        with session.no_autoflush:
            for alb in list(artist.albums):
                if alb.type != VARIOUS_TYPE:
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

    # FIXME: prompt for whether the tags should be updated with the new name if it is new.
