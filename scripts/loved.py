#!/usr/bin/env python
import sys
import json
from pathlib import Path
import sqlalchemy.exc
import mishmash.database
from mishmash.orm import Track, Artist, Album
from eyed3.core import *

ALBUM_TYPE_ORDER = [LP_TYPE, EP_TYPE, SINGLE_TYPE, COMP_TYPE, VARIOUS_TYPE, LIVE_TYPE, DEMO_TYPE]


def chooseAlbum(albums):
    def _typeKey(a):
        return list(reversed(ALBUM_TYPE_ORDER)).index(a.type) + 1

    def _dateKey(a):
        return a.getBestDate()

    # 1: Prefer older, older is better
    albums.sort(key=_dateKey)
    # 2: Prefer studio recordings (lp, ep, etc) over live, demos
    albums.sort(key=_typeKey)

    return albums[0]


def sqlstr(s):
    return s.replace("\\", "\\\\").replace("'", "''").replace(":", r"\:")


def queryArtist(session, artist):
    artist = sqlstr(artist)
    return session.execute(f"SELECT * FROM artists WHERE lower(artists.name)='{artist}'")\
                  .fetchall()


def queryTracks(session, loved):
    track = sqlstr(loved["track"].lower())
    artist = sqlstr(loved["artist"].lower())

    return session.execute(f"""
    SELECT * FROM tracks
    WHERE lower(tracks.title) LIKE '%{track}%'
          AND tracks.artist_id=(SELECT id FROM artists WHERE lower(artists.name)='{artist}')
    """).fetchall()


def notFound(session, loved):
    artists = queryArtist(session, loved["artist"])
    if not artists:
        return []
    elif len(artists) > 1:
        # FIXME
        print("FIXME: notFound - multi artist")
        import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME

    title = sqlstr(loved["track"].lower())
    return session.execute(f"""
        SELECT * FROM tracks WHERE tracks.artist_id={artists[0].id}
                                AND levenshtein(lower(tracks.title), '{title}') < 10
    """).fetchall()


### FIXME: Enough with the smarts.. Just ask....

def resolve(session, loved, tracks):
    # Look for exact title matches
    title_matches = list([t for t in tracks if t.title.lower() == loved["track"].lower()])
    if len(title_matches) == 1:
        # Matched one, nice
        return title_matches.pop()
    elif title_matches:
        # Bias sort album and pick head
        album = chooseAlbum([session.query(Album).filter(Album.id == t.album_id).one()
                                for t in title_matches])
        for t in title_matches:
            if t.album_id == album.id:
                return t
    else:
        import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME
        ...

    return None


infile = Path(sys.argv[1])
db_info = mishmash.database.init("postgresql://mishmash:P@r@gonB3lial@172.24.0.7/MishMash")
session = db_info.SessionMaker()

num_loved, num_matches, num_found = 0, 0, 0
for line in infile.read_text().splitlines():
    loved = json.loads(line)
    num_loved += 1

    try:
        tracks = queryTracks(session, loved)
    except sqlalchemy.exc.ProgrammingError as sql_err:
        print("FIXME: dup artist?")
        session.close()
        session = db_info.SessionMaker()
        continue  # FIXME
    except sqlalchemy.exc.StatementError as sql_stm_err:
        import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME
        raise

    track = None
    num_matches += len(tracks)
    if len(tracks) == 0:
        tracks = notFound(session, loved)
        if len(tracks) > 1:
            import pdb; pdb.set_trace()  # FIXME
            pass  # FIXME

    if len(tracks) > 1:
        track = resolve(session, loved, tracks)

    if track is None:
        print("NOT FOUND:", loved)
    else:
        #print("FOUND:", tracks)
        num_found += 1
    # TODO: Tag the love in the DB
    # TODO: Tag the love in the file tag

print("num_loved:", num_loved)
print("num_found:", num_found)
print("num_matches:", num_matches)







