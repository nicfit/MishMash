# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2012  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################
import os
from datetime import datetime
from hashlib import md5

import sqlalchemy as sql
from sqlalchemy import orm, event, types
from sqlalchemy.engine import Engine
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.declarative import declarative_base

from eyed3.utils import guessMimetype
from eyed3.utils import art
from eyed3.core import Date as Eyed3Date
from eyed3.core import ALBUM_TYPE_IDS, VARIOUS_TYPE, LIVE_TYPE

from . import __version__ as VERSION


VARIOUS_ARTISTS_NAME = u"Various Artists"
VARIOUS_ARTISTS_ID = 1


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    '''Allows foreign keeys to work in sqlite.'''
    import sqlite3
    if dbapi_connection.__class__ is sqlite3.Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


Base = declarative_base()

artist_labels = sql.Table("artist_labels", Base.metadata,
                          sql.Column("artist_id", sql.Integer,
                                     sql.ForeignKey("artists.id")),
                          sql.Column("label_id", sql.Integer,
                                     sql.ForeignKey("labels.id")),
                         )

album_labels = sql.Table("album_labels", Base.metadata,
                         sql.Column("album_id", sql.Integer,
                                    sql.ForeignKey("albums.id")),
                         sql.Column("label_id", sql.Integer,
                                    sql.ForeignKey("labels.id")),
                        )

track_labels = sql.Table("track_labels", Base.metadata,
                         sql.Column("track_id", sql.Integer,
                                    sql.ForeignKey("tracks.id")),
                         sql.Column("label_id", sql.Integer,
                                    sql.ForeignKey("labels.id")),
                        )

artist_images = sql.Table("artist_images", Base.metadata,
                          sql.Column("artist_id", sql.Integer,
                                     sql.ForeignKey("artists.id")),
                          sql.Column("img_id", sql.Integer,
                                     sql.ForeignKey("images.id")),
                         )

album_images = sql.Table("album_images", Base.metadata,
                         sql.Column("album_id", sql.Integer,
                                    sql.ForeignKey("albums.id")),
                         sql.Column("img_id", sql.Integer,
                                    sql.ForeignKey("images.id")),
                        )


class OrmObject(object):
    @staticmethod
    def initTable(session):
        pass

    def __repr__(self):
        attrs = []
        for key in self.__dict__:
            if not key.startswith('_'):
                attrs.append((key, getattr(self, key)))
        return self.__class__.__name__ + '(' + ', '.join(x[0] + '=' +
                                            repr(x[1]) for x in attrs) + ')'


class Meta(Base, OrmObject):
    __tablename__ = "meta"

    # Columns
    version = sql.Column(sql.String(32), nullable=False, primary_key=True)
    last_sync = sql.Column(sql.DateTime)

    @staticmethod
    def initTable(session):
        session.add(Meta(version=VERSION))


def _getSortName(name):
    from . import util
    suffix, prefix = util.splitNameByPrefix(name)
    return u"%s, %s" % (suffix, prefix) if prefix else name


class Artist(Base, OrmObject):
    __tablename__ = "artists"
    __table_args__ = (sql.UniqueConstraint("name",
                                           "origin_city",
                                           "origin_state",
                                           "origin_country",
                                           name="artist_uniq_constraint"), {})

    # Columns
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.Unicode(128), nullable=False, index=True)
    sort_name = sql.Column(sql.Unicode(128), nullable=False)
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    origin_city = sql.Column(sql.Unicode(32))
    origin_state = sql.Column(sql.Unicode(32))
    origin_country = sql.Column(sql.String(3))

    # Relations
    albums = orm.relation("Album", cascade="all")
    '''all albums by the artist'''
    tracks = orm.relation("Track", cascade="all")
    '''all tracks by the artist'''
    labels = orm.relation("Label", secondary=artist_labels)
    '''one-to-many (artist->label) and many-to-one (label->artist)'''
    images = orm.relation("Image", secondary=artist_images, cascade="all")
    '''one-to-many artist images.'''

    @staticmethod
    def initTable(session):
        va = Artist(name=VARIOUS_ARTISTS_NAME)
        session.add(va)
        session.flush()
        if va.id != VARIOUS_ARTISTS_ID:
            raise RuntimeError("Unable to provision various artists")

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
        from .util import normalizeCountry
        origins = [o for o in [normalizeCountry(self.origin_country,
                                                target=country_code,
                                                title_case=title_case),
                               self.origin_state,
                               self.origin_city]
                     if o]
        origins = origins[:n]
        origins.reverse()
        return u", ".join(origins)

    @orm.validates("name")
    def _setName(self, key, value):
        '''This exists merely to keep sort_name in sync.'''
        if not value:
            raise ValueError("Artist.name is not nullable")
        self.sort_name = _getSortName(value)
        return value

    @orm.validates("origin_country")
    def _setOriginCountry(self, key, value):
        from .util import normalizeCountry
        if value is None:
            return None
        return normalizeCountry(value, target="iso3c", title_case=False)

    @staticmethod
    def checkUnique(artists):
        vals = []
        for a in artists:
            v = (a.name, a.origin_city, a.origin_state, a.origin_country)
            if v in vals:
                return False
            vals.append(v)
        return True


class AlbumDate(TypeDecorator):
    '''Custom column type for eyed3.core.Date objects. That is, dates than
    can have empty rather than default date fields. For example, 1994 with no
    month and day is different than 1994-01-01, as datetime provides.'''
    impl = types.String(24)

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
                                           "artist_id"), {})

    _types_enum = sql.Enum(*ALBUM_TYPE_IDS, name="album_types")

    # Columns
    id = sql.Column(sql.Integer, primary_key=True)
    title = sql.Column(sql.Unicode(128), nullable=False, index=True)
    type = sql.Column(_types_enum, nullable=False, default=ALBUM_TYPE_IDS[0])
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    release_date = sql.Column(AlbumDate)
    original_release_date = sql.Column(AlbumDate)
    recording_date = sql.Column(AlbumDate)

    # Foreign keys
    artist_id = sql.Column(sql.Integer, sql.ForeignKey("artists.id"),
                           nullable=False, index=True)

    # Relations
    artist = orm.relation("Artist")
    tracks = orm.relation("Track", order_by="Track.track_num",
                          cascade="all")
    labels = orm.relation("Label", secondary=album_labels)
    images = orm.relation("Image", secondary=album_images, cascade="all")
    '''one-to-many album images.'''

    def getBestDate(self):
        from eyed3.utils import datePicker
        return datePicker(self,
                          prefer_recording_date=bool(self.type == LIVE_TYPE))

    @property
    def duration(self):
        return sum([t.time_secs for t in self.tracks])


class Track(Base, OrmObject):
    __tablename__ = "tracks"

    # Columns
    id = sql.Column(sql.Integer, primary_key=True)
    path = sql.Column(sql.String(512), nullable=False, unique=True, index=True)
    size_bytes = sql.Column(sql.Integer, nullable=False)
    ctime = sql.Column(sql.DateTime(), nullable=False)
    mtime = sql.Column(sql.DateTime(), nullable=False)
    date_added = sql.Column(sql.DateTime(), nullable=False,
                            default=datetime.now)
    time_secs = sql.Column(sql.Integer, nullable=False)
    title = sql.Column(sql.Unicode(128), nullable=False, index=True)
    track_num = sql.Column(sql.SmallInteger)
    track_total = sql.Column(sql.SmallInteger)
    media_num = sql.Column(sql.SmallInteger)
    media_total = sql.Column(sql.SmallInteger)
    bit_rate = sql.Column(sql.SmallInteger)
    variable_bit_rate = sql.Column(sql.Boolean)

    # Foreign keys
    artist_id = sql.Column(sql.Integer, sql.ForeignKey("artists.id"),
                           nullable=False, index=True)
    album_id = sql.Column(sql.Integer, sql.ForeignKey("albums.id"),
                          nullable=True, index=True)
    # Relations
    artist = orm.relation("Artist")
    album = orm.relation("Album")
    labels = orm.relation("Label", secondary=track_labels)

    def __init__(self, **kwargs):
        '''Along with the column args a ``audio_file`` keyword may be passed
        for this class to use for initialization.'''

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
        self.title = tag.title
        self.track_num, self.track_total = tag.track_num
        self.variable_bit_rate, self.bit_rate = info.bit_rate
        self.media_num, self.media_total = tag.disc_num


class Label(Base, OrmObject):
    __tablename__ = "labels"

    # Columns
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.Unicode(64), nullable=False, unique=True)


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
    _types_enum = sql.Enum(*IMAGE_TYPES, name="image_types")

    id = sql.Column(sql.Integer, primary_key=True)
    type = sql.Column(_types_enum, nullable=False)
    mime_type = sql.Column(sql.String(32), nullable=False)
    md5 = sql.Column(sql.String(32), nullable=False)
    size = sql.Column(sql.Integer, nullable=False)
    description = sql.Column(sql.String(1024), nullable=False)
    '''The description will be the base file name when the source if a file.'''
    data = orm.deferred(sql.Column(sql.LargeBinary, nullable=False))

    @staticmethod
    def fromTagFrame(img, type):
        md5hash = md5()
        md5hash.update(img.image_data)

        return Image(type=type,
                     description=img.description,
                     mime_type=img.mime_type,
                     md5=md5hash.hexdigest(),
                     size=len(img.image_data),
                     data=img.image_data)

    @staticmethod
    def fromFile(path, type):
        md5hash = md5()

        img = open(path, "rb")
        data = img.read()
        img.close()

        md5hash.update(data)

        return Image(type=type,
                     mime_type=guessMimetype(path),
                     md5=md5hash.hexdigest(),
                     size=len(data),
                     data=data)


TYPES = [Meta, Label, Artist, Album, Track, Image]
LABELS = [artist_labels, album_labels, track_labels,
          artist_images, album_images]
TABLES = [T.__table__ for T in TYPES] + LABELS
'''All the table instances.  Order matters (esp. for postgresql). The
tables are created in normal order, and dropped in reverse order.'''
ENUMS = [Image._types_enum, Album._types_enum]
