#!/usr/bin/env python
import os
from collections import Counter
import mishmash.database
from mishmash.orm import Artist
from PyInquirer import prompt


def sqlstr(s):
    return s.replace("'", "''")


def handleDupArtist(session, artists):
    OTHER = "Other (enter a new name)"

    # Artist names counted by number of tracks
    artist_names = Counter({a.name: len(a.tracks) for a in artists})
    mc_name = artist_names.most_common(1)[0][0]

    # TODO
    if len(artist_names) == 1:
        print("TODO: not a string case issue")
        return

    print(f"\n-- Multiple artists named '{mc_name}'")
    if prompt({"name": "merge",
               "type": "confirm",
               "message": f"Merge artists?",
               "default": False,
               })["merge"]:

        choices = [name for name, _ in artist_names.most_common()] + [OTHER]
        artist_name = prompt({"name": "name",
                              "type": "list",
                              "message": "Choose correct artist name.",
                              "choices": choices,
                              })["name"]
        if artist_name == OTHER:
            artist_name = prompt({"name": "name",
                                  "type": "input",
                                  "message": "Enter correct artist name.",
                                  })["name"]

        merge(session, artists, artist_name)


def merge(session, artists, artist_name):
    print(f"Merge {artist_name}")  # TODO
    ...


db_info = mishmash.database.init(os.getenv("MISHMASH_DBURL"))
session = db_info.SessionMaker()

_checked = set()
for artist in session.query(Artist).all():
    lower_name = artist.name.lower()
    if lower_name in _checked:
        continue
    _checked.add(lower_name)

    dup_artists = session.query(Artist).filter(Artist.name.ilike(artist.name)).all()
    if len(dup_artists) > 1:
        handleDupArtist(session, dup_artists)
