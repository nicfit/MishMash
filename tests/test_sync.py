from .factories import (Mp3AudioFileFactory, EpFactory, LibraryFactory,
                        DirectoryStructure)
from mishmash.__main__ import MishMash


def test_sync(tmpdir, mishmash_cmd):
    lib = LibraryFactory(name="I don't like you")
    ep = EpFactory(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2,
                   track_titles=("Tide", "You Gotta Have Someone"),
                   temp_dir=str(tmpdir))

    dir_struct = DirectoryStructure.PREFERRED
    dir_struct.apply(*[t._mp3_file for t in ep.tracks], root_dir=tmpdir)

    mishmash_cmd(["sync", str(tmpdir)])

    # TODO: load the DB and validate
