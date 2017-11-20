from pathlib import Path
import eyed3.id3
from eyed3.core import LP_TYPE, EP_TYPE
from . import factories


def test_TagFactory():
    tag = factories.TagFactory.build()
    assert isinstance(tag, eyed3.id3.Tag)
    assert tag.title.startswith("Track title #")
    assert tag.artist == "Artist"
    assert tag.album == "Album"
    assert tag.album_artist == None
    assert tag.track_num == (None, None)

    tag2 = factories.TagFactory.build(title="Another title", track_num=2)
    assert tag2.title == "Another title"
    assert tag2.artist == tag.artist
    assert tag2.album == tag.album
    assert tag2.album_artist == None
    assert tag2.track_num == (2, None)


def test_Mp3AudioFileFactory(mp3audiofile):
    assert mp3audiofile.path is not None
    assert Path(mp3audiofile.path).exists()
    assert mp3audiofile.tag is not None
    assert mp3audiofile.tag.title is not None
    assert mp3audiofile.tag.artist is not None
    assert mp3audiofile.tag.album_artist is None


def test_AlbumFactory():
    album = factories.AlbumFactory()
    assert album.type == LP_TYPE
    assert factories.LP_SIZE[0] <= len(album.tracks) <= factories.LP_SIZE[1]

    title = album.title
    assert title
    artist = album.artist
    assert artist
    ogdate = album.original_release_date
    assert ogdate
    rdate = album.release_date

    tracks = album.tracks
    assert all([bool(t.artist.name == artist) for t in tracks])
    assert all([bool(t.album.title == title) for t in tracks])
    assert all([bool(t.album.original_release_date == ogdate) for t in tracks])
    assert all([(str(t.album.release_date), str(rdate)) for t in tracks])


def test_EpFactory():
    ep = factories.EpFactory()
    assert ep.type == EP_TYPE
    assert factories.EP_SIZE[0] <= len(ep.tracks) <= factories.EP_SIZE[1]


def test_LibraryFactory():
    lib = factories.LibraryFactory()
    assert lib.name
    assert lib.last_sync is None
    assert lib.id is None

    lib = factories.LibraryFactory(name="Music")
    assert lib.name == "Music"
