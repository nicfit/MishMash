#!/usr/bin/env python
"""Duplicate artist finder/fixer.
"""
import os
import sys
import argparse
from collections import Counter

import inquirer
import mishmash.util
import mishmash.database

from eyed3.core import ArtistOrigin, VARIOUS_TYPE
from mishmash.orm import Artist, Library
from sqlalchemy.orm.exc import NoResultFound

OTHER_CHOICE = "Other (enter a new name)"
OTHER_PROMPT = "Alternate name)"


def sqlstr(s):
    # FIXME: unused
    return s.replace("'", "''")


def inquirer_list_with_other_option(message, choices, other_choice=OTHER_CHOICE,
                                    other_prompt=OTHER_PROMPT):
    choices = list(choices) + [other_choice]
    choice = inquirer.list_input(message, choices=choices)
    if choice == other_choice:
        choice = inquirer.text(other_prompt)
    return choice


def handleDupArtist(session, artists, fix=False, fix_tags=True, dry_run=False):

    # Artist names counted by number of tracks
    weighted_artists = Counter({a: len(a.tracks) for a in artists})

    if len(set([a.name for a in weighted_artists.keys()])) == 1:
        # TODO
        print("TODO: not a string case issue. The Giraffes land here.")
        return

    # Reduce to a common origin.
    city, state, country = None, None, None
    origins = list(
            filter(lambda x: (x[0] or x[1] or x[2]),
                   [(a.origin_city, a.origin_state, a.origin_country) for a in weighted_artists.keys()])
    )
    if origins:
        if len(origins) > 1:
            ...
            raise NotImplemented("FIXME")
        else:
            city, state, country = origins.pop()
            assert len(origins) == 0

    dup_artists = "\n  ".join(
        [f"- {a.name} ({weighted_artists[a]} entries)" for a in weighted_artists]
    )
    print(f"\nDuplicate artist name:\n  {dup_artists}")

    if fix is False:
        return
    # Deal with the dup...

    if inquirer.confirm("Merge artists?", default=False):
        choices = [a.name for a, _ in weighted_artists.most_common()]
        artist_name = inquirer_list_with_other_option("Choose correct artist name", choices=choices)

        merge(session, weighted_artists, artist_name, (city, state, country), fix_tags, dry_run)
        print(f"{artist_name} merged!")


def merge(session, artists: Counter, final_artist_name, final_origin, fix_tags, dry_run=False):
    if len(artists) < 2:
        raise ValueError("More than one artist required for merging.")

    # Reuse is with the most use
    final_artist = artists.most_common()[0][0]
    other_artists = [a[0] for a in artists.most_common()[1:]]

    # Update name
    final_artist.name = final_artist_name

    # Update origin
    (final_artist.origin_city,
     final_artist.origin_state,
     final_artist.origin_city) = final_origin

    tag_files = list(final_artist.tracks) if fix_tags else None

    # Update the other artist albums and tracks
    for artist in other_artists:
        if artist.name.startswith("LIf"):
            import pdb; pdb.set_trace()  # FIXME
            pass  # FIXME
        with session.no_autoflush:
            # Albums
            for album in list(artist.albums):
                if album.type != VARIOUS_TYPE:
                    album.artist_id = final_artist.id
                    artist.albums.remove(album)
                    with session.no_autoflush:
                        final_artist.albums.append(album)

                # Album tracks
                for track in album.tracks:
                    if track.artist_id == artist.id:
                        # gotta check in case album is type various
                        track.artist_id = final_artist.id
            artist.albums.clear()

            # Update singles
            for track in artist.getTrackSingles():
                track.artist_id = final_artist.id

                with session.no_autoflush:
                    final_artist.tracks.append(track)

                if fix_tags:
                    tag_files.append(track)
            artist.tracks.clear()

        # flush to get new artist ids in sync before delete, otherwise
        # cascade happens.
        session.flush()

        session.delete(artist)
        session.flush()

    if fix_tags:
        print(f"Checking {len(tag_files)} tag files...")
        import pdb; pdb.set_trace()  # FIXME
        for track in tag_files:
            edits = []

            # FIXME: hardcoded mapping
            audio_file = track.loadAudioFile(path_mapping={"/media/music/": "/home/travis/Music/"})
            tag = audio_file.tag

            curr_artist = tag.artist or ""
            if curr_artist != final_artist.name:
                edits.append(f"artist: {curr_artist} --> {final_artist.name}")
                tag.artist = final_artist.name

            # Matching artist and album_artist, so the name update happens here as well
            curr_album_artist = tag.album_artist or ""
            if curr_album_artist and curr_artist != curr_album_artist:
                edits.append(f"album-artist: {curr_album_artist} --> {final_artist.name}")
                tag.album_artist = final_artist.name

            artist_origin = ArtistOrigin(*final_origin) or None
            if tag.artist_origin != artist_origin:
                edits.append(f"artist-origin: {tag.artist_origin} --> {artist_origin}")
                tag.artist_origin = artist_origin

            if edits:
                edits_txt = " | ".join(edits)
                print(f"Updating file: {audio_file.path}\n\t{edits_txt}")

                if not dry_run:
                    tag.save(audio_file.path)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("-F", "--fix", action="store_true", dest="fix",
                     help="Fix the duplicates interactively.")
    cli.add_argument("--no-fix-tag", action="store_true", dest="no_fix_tag",
                     help="When fixing, skip updating the file tag. Only used with --fix.")
    cli.add_argument("-n", "--dry-run", action="store_true", dest="dry_run",
                     help="Refrains from commit or tag files when used with --fix.")
    cli.add_argument("artist", nargs="?", metavar="artist-name",
                     help="An artist name to search/fix.")
    mishmash.util.addLibraryArguments(cli, "?")

    args = cli.parse_args()

    db_info = mishmash.database.init(os.getenv("MISHMASH_DBURL"))
    session = db_info.SessionMaker()

    try:
        lib = session.query(Library).filter(Library.name == args.lib).one()
    except NoResultFound:
        print(f"Library '{args.lib}' not found.", file=sys.stderr)
        return 1

    _checked = set()
    if args.artist:
        artist_query = session.query(Artist).filter(Artist.lib_id == lib.id)\
                                            .filter(Artist.name == args.artist)
    else:
        artist_query = session.query(Artist).filter(Artist.lib_id == lib.id)

    for artist in artist_query.all():
        lower_name = artist.name.lower()

        if lower_name in _checked:
            continue
        _checked.add(lower_name)

        dup_artists = session.query(Artist).filter(Artist.lib_id == lib.id)\
                                           .filter(Artist.name.ilike(artist.name))\
                                           .all()
        if len(dup_artists) > 1:
            handleDupArtist(session, dup_artists, args.fix, not args.no_fix_tag,
                            dry_run=args.dry_run)

    if not args.dry_run:
        session.commit()


if __name__ == "__main__":
    status = 1
    try:
        status = main() or 0
    except KeyboardInterrupt:
        pass
    except Exception as uncaught:
        import traceback
        print(f"Uncaught exception:\n{traceback.format_exc()}")
    finally:
        sys.exit(status)
