from .core import *   # noqa: F403

# Core orm
TYPES = [Meta, Library, Tag, Artist, Album, Track, Image]  # noqa: F405
TAGS = [artist_tags, album_tags, track_tags, artist_images, album_images]  # noqa: F405
IMAGE_TABLES = [artist_images, album_images]  # noqa: F405
ENUMS = [Image._types_enum, Album._types_enum]  # noqa: F405

# All the table instances. Order matters (esp. for postgresql). The tables are created in
# normal order, and dropped in reverse order.
TABLES = [T.__table__ for T in TYPES] + TAGS + IMAGE_TABLES
