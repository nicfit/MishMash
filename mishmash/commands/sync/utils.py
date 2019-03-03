import os
import nicfit
from nicfit.console import pout
from nicfit.console.ansi import Fg

from ...orm import VARIOUS_ARTISTS_ID
from ...orm import Artist, Track, Album

log = nicfit.getLogger(__name__)


def deleteOrphans(session):
    num_orphaned_artists = 0
    num_orphaned_albums = 0
    num_orphaned_tracks = 0
    found_ids = set()

    # Tracks
    for track in session.query(Track).all():
        if not os.path.exists(track.path):
            pout(Fg.red("Removing track") + ": " + track.path)
            session.delete(track)
            num_orphaned_tracks += 1
            log.warn("Deleting track: %s" % str(track))
    session.flush()

    # Albums
    found_ids.clear()
    for album in session.query(Album).all():
        if album.id in found_ids:
            continue

        any_track = session.query(Track).filter(Track.album_id == album.id).first()
        if not any_track:
            log.warn("Deleting album: %s" % str(album))
            session.delete(album)
            num_orphaned_albums += 1
        else:
            found_ids.add(album.id)
    session.flush()

    # Artists
    found_ids.clear()
    for artist in session.query(Artist).all():
        if (artist.id == VARIOUS_ARTISTS_ID or
                artist.id in found_ids):
            continue

        any_track = session.query(Track).filter(Track.artist_id == artist.id) \
                                        .first()
        any_album = session.query(Album).filter(Album.artist_id == artist.id) \
                                        .first()
        if not any_track and (not any_album or not any_album.tracks):
            log.warn("Deleting artist: %s" % str(artist))
            session.delete(artist)
            num_orphaned_artists += 1
        else:
            found_ids.add(artist.id)
    session.flush()

    return (num_orphaned_tracks, num_orphaned_artists, num_orphaned_albums)


def syncImage(img, current, session):
    """Add or updated the Image."""
    def _img_str(i):
        return "%s - %s" % (i.type, i.description)

    for db_img in current.images:
        img_info = (img.type, img.md5, img.size)
        db_img_info = (db_img.type, db_img.md5, db_img.size)

        if db_img_info == img_info:
            img = None
            break
        elif (db_img.type == img.type and
                db_img.description == img.description):

            if img.md5 != db_img.md5:
                # Update image
                current.images.remove(db_img)
                current.images.append(img)
                session.add(current)
                pout(Fg.green("Updating image") + ": " + _img_str(img))
            img = None
            break

    if img:
        # Add image
        current.images.append(img)
        session.add(current)
        pout(Fg.green("Adding image") + ": " + _img_str(img))
