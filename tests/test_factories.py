from pathlib import Path
import eyed3.id3
from factories import TagFactory


def test_TagFactory():
    tag = TagFactory.build()
    assert isinstance(tag, eyed3.id3.Tag)
    assert tag.title.startswith("Track title #")
    assert tag.artist == "Artist"
    assert tag.album == "Album"
    assert tag.album_artist == tag.artist
    assert tag.track_num == (None, None)

    tag2 = TagFactory.build(title="Another title", track_num=2)
    assert tag2.title == "Another title"
    assert tag2.artist == tag.artist
    assert tag2.album == tag.album
    assert tag2.album_artist == tag.album_artist
    assert tag2.track_num == (2, None)


def test_Mp3AudioFileFactory(mp3audiofile):
    assert mp3audiofile.path is not None
    assert Path(mp3audiofile.path).exists()
    assert mp3audiofile.tag is not None
    assert mp3audiofile.tag.title is not None
    assert mp3audiofile.tag.artist is not None
    if mp3audiofile.tag.version[0] == 1:
        assert mp3audiofile.tag.album_artist is None
    else:
        assert mp3audiofile.tag.album_artist is not None
