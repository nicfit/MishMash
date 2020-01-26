from .core import *
from . import user

# Core orm
TYPES = [Meta, Library, Tag, Artist, Album, Track, Image]
TAGS = [artist_tags, album_tags, track_tags, artist_images, album_images]
IMAGE_TABLES = [artist_images, album_images]
ENUMS = [Image._types_enum, Album._types_enum]

# User orm
TYPES += [user.User]

# All the table instances. Order matters (esp. for postgresql). The tables are created in
# normal order, and dropped in reverse order.
TABLES = [T.__table__ for T in TYPES] + TAGS + IMAGE_TABLES


