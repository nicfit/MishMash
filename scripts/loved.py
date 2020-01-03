#!/usr/bin/env python
import sys
import json
from pathlib import Path
import sqlalchemy.exc
import sqlalchemy.orm.exc
import mishmash.database
from mishmash.orm import Album
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

    print("CHOSE:", albums[0], "\nover\n", albums[1:])
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
        # Tracks with album_id==None are skipped
        album = chooseAlbum([session.query(Album).filter(Album.id == t.album_id).one()
                                for t in title_matches if t.album_id])
        for t in title_matches:
            if t.album_id == album.id:
                return t
    else:
        # No title matches.

        # Startswith matches
        prefix_matches = list([t for t in tracks
                                    if t.title.lower().startswith(loved["track"].lower())])
        if prefix_matches:
            # FIXME: this choice got be made better
            print("CHOSE:", prefix_matches[0], "\nover\n", prefix_matches[1:])
            return prefix_matches[0]

        import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME
        ...

    return None


infile = Path(sys.argv[1])
db_info = mishmash.database.init(os.getenv("MISHMASH_DBURL"))
session = db_info.SessionMaker()

num_loved, num_matches, num_found = 0, 0, 0
for line in infile.read_text().splitlines():
    # FIXME
    if "Deicide" in line:
        #import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME
    loved = json.loads(line)
    num_loved += 1

    if ((loved["track"][0], loved["track"][-1]) == ('"', '"')
            or (loved["track"][0], loved["track"][-1]) == ("'", "'")):
        # Removed quotes
        loved["track"] = loved["track"][1:-1]

    try:
        tracks = queryTracks(session, loved)
    except sqlalchemy.exc.ProgrammingError as sql_err:
        print("FIXME: dup artist?")
        #import pdb; pdb.set_trace()  # FIXME
        pass  # FIXME
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

    if len(tracks) == 1:
        track = tracks[0]
    elif len(tracks) > 1:
        track = resolve(session, loved, tracks)

    if track:
        print("FOUND:", loved)
        num_found += 1
    else:
        print("NOT FOUND:", loved)

    # TODO: Tag the love in the DB
    # TODO: Tag the love in the file tag

print("num_loved:", num_loved)
print("num_found:", num_found)
print("num_matches:", num_matches)







