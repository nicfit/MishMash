import datetime
import pytest
from sqlalchemy.exc import IntegrityError, DataError
import mishmash
from mishmash.orm import (Meta, Library, Artist, Album, Track, Image,
                          NULL_LIB_ID, NULL_LIB_NAME,
                          MAIN_LIB_ID, MAIN_LIB_NAME)


def test_meta_table(session):
    metadata = session.query(Meta).one()
    assert metadata.version == mishmash.version
    assert metadata.last_sync is None


def test_meta_table_write(session):
    metadata = session.query(Meta).one()
    metadata.version = "1.2.3"
    t = datetime.datetime.utcnow()
    metadata.last_sync = t
    session.add(metadata)
    session.commit()

    metadata = session.query(Meta).one()
    assert metadata.version == "1.2.3"
    assert metadata.last_sync == t


def test_libraries_table(session):
    # Default rows, for __null__ and Music
    default_rows = session.query(Library).all()
    assert len(default_rows) == 2
    assert default_rows[0].id == NULL_LIB_ID
    assert default_rows[0].name == NULL_LIB_NAME
    assert default_rows[0].last_sync is None
    assert default_rows[1].id == MAIN_LIB_ID
    assert default_rows[1].name == MAIN_LIB_NAME
    assert default_rows[1].last_sync is None


def test_ArtistNoLib(session):
    session.add(Artist(name="Pantera"))
    with pytest.raises(IntegrityError):
        session.commit()

def test_Artist(session, db_library):
    lid = db_library.id
    session.add(Artist(name="The Roots", lib_id=lid))
    session.commit()
    assert session.query(Artist).filter_by(name="The Roots", lib_id=lid).one()


def test_Track(session, db_library, mp3audiofile):
    lid = db_library.id
    artist = Artist(name=mp3audiofile.tag.artist, lib_id=lid)
    session.add(artist)
    session.flush()
    session.add(Track(audio_file=mp3audiofile, lib_id=lid, artist_id=artist.id))
    session.commit()
    assert session.query(Track).filter_by(title=mp3audiofile.tag.title,
                                          lib_id=lid).one()


def test_MetaTooBig(session, db_library, request):
    lid = db_library.id
    v = "!" * (Meta.VERSION_LIMIT + 1)
    session.add(Meta(version=v))
    if "sqlite" in request.keywords:
        session.commit()
        assert session.query(Meta).filter_by(version=v).one()
    else:
        with pytest.raises(DataError):
            session.commit()


def test_LibraryTooBig(session, db_library, request):
    lid = db_library.id
    v = "!" * (Library.NAME_LIMIT + 1)
    session.add(Library(name=v))
    if "sqlite" in request.keywords:
        session.commit()
        assert session.query(Library).filter_by(name=v).one()
    else:
        with pytest.raises(DataError):
            session.commit()


def test_ColumnTooBigTruncates(session, db_library, request, mp3audiofile):
    artist_name = "*" * (Artist.NAME_LIMIT + 1)
    city = "c" * (Artist.CITY_LIMIT + 1)
    state = "s" * (Artist.STATE_LIMIT + 1)
    artist = Artist(name=artist_name, origin_city=city, origin_state=state,
                    origin_country="United States", lib_id=db_library.id)
    session.add(artist)
    session.commit()
    artist = session.query(Artist)\
                    .filter_by(name=artist_name[:Artist.NAME_LIMIT],
                               origin_city=city[:Artist.CITY_LIMIT],
                               origin_state=state[:Artist.STATE_LIMIT],
                               origin_country="USA").one()
    assert artist

    album_name = "*" * (Album.TITLE_LIMIT + 1)
    album = Album(title=album_name, artist_id=artist.id, lib_id=db_library.id)
    session.add(album)
    session.commit()
    album = session.query(Album) \
                   .filter_by(title=album_name[:Album.TITLE_LIMIT]).one()
    assert album

    track_title = "*" * (Track.TITLE_LIMIT + 1)
    track = Track(lib_id=db_library.id, artist_id=artist.id, album_id=album.id)
    track.update(mp3audiofile)
    track.title = track_title
    session.add(track)
    session.commit()
    track = session.query(Track) \
                   .filter_by(title=track_title[:Track.TITLE_LIMIT]).one()
    assert track


def test_ImageMd5Validator(session, db_library, request, mp3audiofile):
    img = Image(type=Image.FRONT_COVER_TYPE, size=666,
                md5="48a6de198166ad9806f1a2172f2947df",
                mime_type="img/jpg", description="Iceburn",
                data=b"\xde\xad\xbe\xef")
    session.add(img)
    session.commit()
    img = session.query(Image).filter_by(data=b"\xde\xad\xbe\xef").one()
    assert img

    # Invalid md5
    with pytest.raises(ValueError):
        img.md5 = "Warzone"

    with pytest.raises(ValueError):
        img = Image(type=Image.FRONT_COVER_TYPE, size=666, md5="12345",
                    mime_type="img/sexy", description="Iceburn",
                    data=b"\xde\xad\xbe\xef")

def test_ImageLimits(session, db_library, request, mp3audiofile):
    desc = "d" * (Image.DESC_LIMIT + 1)
    img = Image(type=Image.FRONT_COVER_TYPE, size=666,
                md5="48a6de198166ad9806f1a2172f2947df",
                mime_type="img/png", description=desc,
                data=b"\xde\xad\xbe\xef")
    session.add(img)
    session.commit()
    img = session.query(Image).filter_by(description=desc[:Image.DESC_LIMIT])\
                 .one()
    assert img

def test_ImageType(session, db_library, request, mp3audiofile):
    img = Image(type="Beyond", size=666,
                md5="48a6de198166ad9806f1a2172f2947df",
                mime_type="img/jpg", description="Iceburn",
                data=b"\xde\xad\xbe\xef")
    session.add(img)

    if "sqlite" in request.keywords:
        with pytest.raises(IntegrityError):
            session.commit()
    else:
        assert "postgresql" in request.keywords
        with pytest.raises(DataError):
            session.commit()

