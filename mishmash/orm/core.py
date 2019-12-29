"""
Object to relational database mappings for all tables.
"""
import os
import re
from hashlib import md5
from datetime import datetime
from gettext import gettext as _

import sqlalchemy as sql
from sqlalchemy.engine import Engine
from sqlalchemy.types import TypeDecorator
from sqlalchemy import orm, event, types, Sequence
from sqlalchemy.ext.declarative import declarative_base

import eyed3
from eyed3.utils import art
from eyed3.utils import guessMimetype
from eyed3.core import Date as Eyed3Date
from eyed3.core import ALBUM_TYPE_IDS, VARIOUS_TYPE, LIVE_TYPE
from eyed3.id3 import ID3_V1_0, ID3_V1_1, ID3_V2_2, ID3_V2_3, ID3_V2_4, versionToString

VARIOUS_ARTISTS_ID = 1
VARIOUS_ARTISTS_NAME = _("Various Artists")
NULL_LIB_ID = 1
NULL_LIB_NAME = "__null_lib__"
MAIN_LIB_ID = 2
MAIN_LIB_NAME = _("Music")
DATE_LIMIT = 24

convention = {
  "ix": 'ix_%(column_0_label)s',
  "uq": "uq_%(table_name)s_%(column_0_name)s",
  "ck": "ck_%(table_name)s_%(constraint_name)s",
  "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
  "pk": "pk_%(table_name)s"
}

Base = declarative_base(metadata=sql.MetaData(naming_convention=convention))

artist_tags = sql.Table("artist_tags", Base.metadata,
                        sql.Column("artist_id", sql.Integer,
                                   sql.ForeignKey("artists.id")),
                        sql.Column("tag_id", sql.Integer,
                                   sql.ForeignKey("tags.id")),
                         )
"""Pivot table 'artist_tags' for mapping an artist ID to a value in the
`tags` table."""

album_tags = sql.Table("album_tags", Base.metadata,
                       sql.Column("album_id", sql.Integer,
                                  sql.ForeignKey("albums.id")),
                       sql.Column("tag_id", sql.Integer,
                                  sql.ForeignKey("tags.id")),
                        )
"""Pivot table 'album_tags' for mapping an album ID to a value in the
`tags` table."""

track_tags = sql.Table("track_tags", Base.metadata,
                       sql.Column("track_id", sql.Integer,
                                  sql.ForeignKey("tracks.id")),
                       sql.Column("tag_id", sql.Integer,
                                  sql.ForeignKey("tags.id")),
                        )
"""Pivot table 'track_tags' for mapping a track ID to a value in the
`tags` table."""

artist_images = sql.Table("artist_images", Base.metadata,
                          sql.Column("artist_id", sql.Integer,
                                     sql.ForeignKey("artists.id")),
                          sql.Column("img_id", sql.Integer,
                                     sql.ForeignKey("images.id")),
                         )
"""Pivot table 'artist_images' for mapping an artist ID to a value in the
`images` table."""

album_images = sql.Table("album_images", Base.metadata,
                         sql.Column("album_id", sql.Integer,
                                    sql.ForeignKey("albums.id")),
                         sql.Column("img_id", sql.Integer,
                                    sql.ForeignKey("images.id")),
                        )
"""Pivot table 'album_images' for mapping an album ID to a value in the
`images` table."""


class OrmObject(object):
    """Base classes for all other mishmash.orm classes."""

    @staticmethod
    def _truncate(string, limit):
        # TODO: Append invisible marker to signal truncation as to NOT reflect
        # TODO: in the original source
        if string and len(string) > limit:
            string = string[:limit]
        return string

    def __repr__(self):  # pragma: nocover
        """Dump the object state and return it as a strings."""
        attrs = []
        for key in self.__dict__:
            if not key.startswith('_'):
                attrs.append((key, getattr(self, key)))
        return self.__class__.__name__ + '(' + \
               ', '.join(x[0] + '=' + repr(x[1]) for x in attrs) + ')'


class Meta(Base, OrmObject):
    """Table ``meta`` used for storing database schema version, timestamps,
    and any other metadata about the music collection."""
    __tablename__ = "meta"
    VERSION_LIMIT = 32

    # Columns
    version = sql.Column(sql.String(VERSION_LIMIT), nullable=False,
                         primary_key=True)
    """The MishMash version defines the database schema."""
    last_sync = sql.Column(sql.DateTime)
    """A UTC timestamp of the last sync operation."""


def getSortName(name):
    from ..util import splitNameByPrefix
    suffix, prefix = splitNameByPrefix(name)
    return "%s, %s" % (suffix, prefix) if prefix else name


class Artist(Base, OrmObject):
    __tablename__ = "artists"
    __table_args__ = (sql.UniqueConstraint("name",
                                           "origin_city",
                                           "origin_state",
                                           "origin_country",
                                           "lib_id",
                                          ), {})

    NAME_LIMIT = 256
    SORT_NAME_LIMIT = NAME_LIMIT + 2

    CITY_LIMIT = 64
    STATE_LIMIT = 32
    COUNTRY_LIMIT = 3

    # Columns
    id = sql.Column(sql.Integer, Sequence("artists_id_seq"), primary_key=True)
    name = sql.Column(sql.Unicode(NAME_LIMIT), nullable=False, index=True)
    sort_name = sql.Column(sql.Unicode(SORT_NAME_LIMIT), nullable=False)
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    origin_city = sql.Column(sql.Unicode(CITY_LIMIT))
    origin_state = sql.Column(sql.Unicode(STATE_LIMIT))
    origin_country = sql.Column(sql.String(COUNTRY_LIMIT))

    # Foreign keys
    lib_id = sql.Column(sql.Integer, sql.ForeignKey("libraries.id"),
                        nullable=False, index=True)

    # Relations
    albums = orm.relation("Album", cascade="all")
    """all albums by the artist"""
    tracks = orm.relation("Track", cascade="all")
    """all tracks by the artist"""
    tags = orm.relation("Tag", secondary=artist_tags)
    """one-to-many (artist->tag) and many-to-one (tag->artist)"""
    images = orm.relation("Image", secondary=artist_images, cascade="all")
    """one-to-many artist images."""
    library = orm.relation("Library")

    def getAlbumsByType(self, album_type):
        if album_type == VARIOUS_TYPE:
            albums = set([t.album for t in self.tracks
                                  if t.album and t.album.type == album_type])
            albums = list(albums)
        else:
            albums = [a for a in self.albums if a.type == album_type]

        return albums

    def getTrackSingles(self):
        tracks = []
        for t in self.tracks:
            if t.album_id is None:
                # Include single files, not associated with an album
                tracks.append(t)
            elif t.album and t.album.artist_id != self.id:
                # Include tracks that the artist appears on.
                tracks.append(t)

        return tracks

    @property
    def url_name(self):
        return self.name.replace("/", "%2f")

    def origin(self, n=3, country_code="country_name", title_case=True):
        from ..util import normalizeCountry
        origins = [o for o in [normalizeCountry(self.origin_country,
                                                target=country_code,
                                                title_case=title_case),
                               self.origin_state,
                               self.origin_city]
                     if o]
        origins = origins[:n]
        origins.reverse()
        return ", ".join(origins)

    @orm.validates("name")
    def _setName(self, key, value):
        if not value:
            raise ValueError("Artist.name is not nullable")
        value = self._truncate(value, self.NAME_LIMIT)
        self.sort_name = getSortName(value)
        return value

    @orm.validates("origin_country")
    def _setOriginCountry(self, _, value):
        from ..util import normalizeCountry
        if value is None:
            return None
        return normalizeCountry(value, target="iso3c", title_case=False)

    @orm.validates("origin_city", "origin_state")
    def _truncateOrigins(self, key, value):
        limit = self.CITY_LIMIT if key == "origin_city" else self.STATE_LIMIT
        return self._truncate(value, limit)

    @staticmethod
    def checkUnique(artists):
        vals = []
        for a in artists:
            v = (a.name, a.origin_city, a.origin_state, a.origin_country)
            if v in vals:
                return False
            vals.append(v)
        return True

    @property
    def is_various_artist(self):
        return self.id == VARIOUS_ARTISTS_ID


class AlbumDate(TypeDecorator):
    """Custom column type for eyed3.core.Date objects. That is, dates than
    can have empty rather than default date fields. For example, 1994 with no
    month and day is different than 1994-01-01, as datetime provides."""
    impl = types.String(DATE_LIMIT)

    def process_bind_param(self, value, dialect):
        if isinstance(value, Eyed3Date):
            return str(value)
        elif value:
            return str(Eyed3Date.parse(value))
        else:
            return None

    def process_result_value(self, value, dialect):
        return Eyed3Date.parse(value) if value else None


class Album(Base, OrmObject):
    __tablename__ = "albums"
    __table_args__ = (sql.UniqueConstraint("title",
                                           "artist_id",
                                           "lib_id",
                                           "release_date",
                                           "recording_date",
                                           "original_release_date",
                                          ), {})

    TITLE_LIMIT = 256
    DATE_LIMIT = DATE_LIMIT
    _types_enum = sql.Enum(*ALBUM_TYPE_IDS, name="album_types")

    # Columns
    id = sql.Column(sql.Integer, Sequence("albums_id_seq"), primary_key=True)
    title = sql.Column(sql.Unicode(TITLE_LIMIT), nullable=False, index=True)
    type = sql.Column(_types_enum, nullable=False, default=ALBUM_TYPE_IDS[0])
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    release_date = sql.Column(AlbumDate)
    original_release_date = sql.Column(AlbumDate)
    recording_date = sql.Column(AlbumDate)

    # Foreign keys
    artist_id = sql.Column(sql.Integer, sql.ForeignKey("artists.id"),
                           nullable=False, index=True)
    lib_id = sql.Column(sql.Integer, sql.ForeignKey("libraries.id"),
                        nullable=False, index=True)

    # Relations
    artist = orm.relation("Artist")
    tracks = orm.relation("Track", order_by="Track.track_num",
                          cascade="all")
    tags = orm.relation("Tag", secondary=album_tags)
    images = orm.relation("Image", secondary=album_images, cascade="all")
    """one-to-many album images."""
    library = orm.relation("Library")

    def getBestDate(self):
        from eyed3.utils import datePicker
        return datePicker(self,
                          prefer_recording_date=bool(self.type == LIVE_TYPE))

    @property
    def duration(self):
        return sum([t.time_secs for t in self.tracks])

    @orm.validates("title")
    def _truncateTitle(self, key, value):
        return self._truncate(value, self.TITLE_LIMIT)


class Track(Base, OrmObject):
    __tablename__ = "tracks"
    __table_args__ = (sql.UniqueConstraint("path",
                                           "lib_id",
                                          ), {})

    METADATA_FORMATS = ["ID3{}".format(versionToString(v))
                            for v in (ID3_V1_0, ID3_V1_1, ID3_V2_2, ID3_V2_3,
                                      ID3_V2_4)]
    _metadata_enum = sql.Enum(*METADATA_FORMATS, name="metadata_format")
    PATH_LIMIT = 2048
    TITLE_LIMIT = 256

    # Columns
    id = sql.Column(sql.Integer, Sequence("tracks_id_seq"), primary_key=True)
    path = sql.Column(sql.String(PATH_LIMIT), nullable=False, index=True)
    size_bytes = sql.Column(sql.Integer, nullable=False)
    ctime = sql.Column(sql.DateTime(), nullable=False)
    mtime = sql.Column(sql.DateTime(), nullable=False)
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    time_secs = sql.Column(sql.Float, nullable=False)
    title = sql.Column(sql.Unicode(TITLE_LIMIT), nullable=False, index=True)
    track_num = sql.Column(sql.SmallInteger)
    track_total = sql.Column(sql.SmallInteger)
    media_num = sql.Column(sql.SmallInteger)
    media_total = sql.Column(sql.SmallInteger)
    bit_rate = sql.Column(sql.SmallInteger)
    variable_bit_rate = sql.Column(sql.Boolean)
    metadata_format = sql.Column(_metadata_enum, nullable=False)

    # Foreign keys
    artist_id = sql.Column(sql.Integer, sql.ForeignKey("artists.id"),
                           nullable=False, index=True)
    album_id = sql.Column(sql.Integer, sql.ForeignKey("albums.id"),
                          nullable=True, index=True)
    lib_id = sql.Column(sql.Integer, sql.ForeignKey("libraries.id"),
                        nullable=False, index=True)

    # Relations
    artist = orm.relation("Artist")
    album = orm.relation("Album")
    tags = orm.relation("Tag", secondary=track_tags)
    library = orm.relation("Library")

    # XXX: test-only
    _mp3_file = None

    def __init__(self, **kwargs):
        """Along with the column args a ``audio_file`` keyword may be passed
        for this class to use for initialization."""

        if "audio_file" in kwargs:
            self.update(kwargs["audio_file"])
            del kwargs["audio_file"]

        super(Track, self).__init__(**kwargs)

    def update(self, audio_file):
        path = audio_file.path
        tag = audio_file.tag
        info = audio_file.info

        self.path = path
        self.size_bytes = info.size_bytes
        self.ctime = datetime.fromtimestamp(os.path.getctime(path))
        self.mtime = datetime.fromtimestamp(os.path.getmtime(path))
        self.time_secs = info.time_secs
        self.title = (tag.title if "\x00" not in tag.title
                                else tag.title.split("\x00")[0])
        self.track_num, self.track_total = tag.track_num
        self.variable_bit_rate, self.bit_rate = info.bit_rate
        self.media_num, self.media_total = tag.disc_num
        self.metadata_format = "ID3{}".format(versionToString(tag.version))

        return self

    @orm.validates("title")
    def _truncateTitle(self, _, value):
        return self._truncate(value, Track.TITLE_LIMIT)

    def loadAudioFile(self, path_mapping=None):
        path = self.path

        path_mapping = path_mapping or {}
        for fm, to in path_mapping.items():
            if path.startswith(fm):
                # Remap path
                path = to + path[len(fm):]

        return eyed3.load(path)


class Tag(Base, OrmObject):
    __tablename__ = "tags"
    __table_args__ = (sql.UniqueConstraint("name",
                                           "lib_id",
                                          ), {})

    NAME_LIMIT = 64

    # Columns
    id = sql.Column(sql.Integer, Sequence("tags_id_seq"), primary_key=True)
    name = sql.Column(sql.Unicode(NAME_LIMIT), nullable=False, unique=False)

    # Foreign keys
    lib_id = sql.Column(sql.Integer, sql.ForeignKey("libraries.id"),
                        nullable=False, index=True)

    # Relations
    library = orm.relation("Library")

    @orm.validates("name")
    def _truncateName(self, key, value):
        return self._truncate(value, self.NAME_LIMIT)


class Image(Base, OrmObject):
    __tablename__ = "images"

    FRONT_COVER_TYPE = art.FRONT_COVER
    BACK_COVER_TYPE = art.BACK_COVER
    MISC_COVER_TYPE = art.MISC_COVER
    LOGO_TYPE = art.LOGO
    ARTIST_TYPE = art.ARTIST
    LIVE_TYPE = art.LIVE
    IMAGE_TYPES = [FRONT_COVER_TYPE, BACK_COVER_TYPE, MISC_COVER_TYPE,
                   LOGO_TYPE, ARTIST_TYPE, LIVE_TYPE]
    MIMETYPE_LIMIT = 32
    MD5_LIMIT = 32
    DESC_LIMIT = 1024
    _types_enum = sql.Enum(*IMAGE_TYPES, name="image_types")

    id = sql.Column(sql.Integer, Sequence("images_id_seq"), primary_key=True)
    type = sql.Column(_types_enum, nullable=False)
    mime_type = sql.Column(sql.String(MIMETYPE_LIMIT), nullable=False)
    md5 = sql.Column(sql.String(MD5_LIMIT), nullable=False)
    size = sql.Column(sql.Integer, nullable=False)
    description = sql.Column(sql.String(DESC_LIMIT), nullable=False)
    """The description will be the base file name when the source if a file."""
    data = orm.deferred(sql.Column(sql.LargeBinary, nullable=False))

    @staticmethod
    def _validMimeType(mt):
        try:
            p1, p2 = mt.split("/")
            return p1 == "image" and p2
        except ValueError:
            # Missing '/'
            return False

    @staticmethod
    def fromTagFrame(img, type_):
        if not Image._validMimeType(img.mime_type):
            return None

        md5hash = md5()
        md5hash.update(img.image_data)

        return Image(type=type_,
                     description=img.description,
                     mime_type=img.mime_type,
                     md5=md5hash.hexdigest(),
                     size=len(img.image_data),
                     data=img.image_data)

    @staticmethod
    def fromFile(path, type_):
        mime_type = guessMimetype(path)
        if not Image._validMimeType(mime_type):
            return None
        md5hash = md5()

        img = open(path, "rb")
        data = img.read()
        img.close()

        md5hash.update(data)

        return Image(type=type_,
                     mime_type=guessMimetype(path),
                     md5=md5hash.hexdigest(),
                     size=len(data),
                     data=data)

    @orm.validates("md5")
    def _validMd5(self, key, value):
        if not re.compile(r"([a-fA-F\d]{32})$").match(value):
            raise ValueError(f"Invalid md5sum: {value}")
        return value

    @orm.validates("description")
    def _validLimits(self, key, value):
        return self._truncate(value, self.DESC_LIMIT)


class Library(Base, OrmObject):
    __tablename__ = "libraries"
    NAME_LIMIT = 64

    # Columns
    id = sql.Column(sql.Integer, Sequence("libraries_id_seq"), primary_key=True)
    name = sql.Column(sql.Unicode(NAME_LIMIT), nullable=False, unique=True)
    last_sync = sql.Column(sql.DateTime)

    _music = []

    def add(self, album):
        self._music.append(album)
        return self

    def albums(self):
        for alb in self._music:
            yield alb

    @classmethod
    def iterall(Class, session, names=None):
        """Iterate over all Library rows found in `session`.
        :param names: Optional sequence of names to filter on.
        """
        names = set(names if names else [])
        for lib in session.query(Class).filter(Class.id > NULL_LIB_ID).all():
            if not names or (lib.name in names):
                yield lib


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Allows foreign keys to work in sqlite."""
    import sqlite3
    if dbapi_connection.__class__ is sqlite3.Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
