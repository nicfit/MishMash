import random
import tempfile
import subprocess

import faker
import factory
import eyed3.id3
import eyed3.mp3
from eyed3.id3 import (ID3_DEFAULT_VERSION, ID3_V1_0, ID3_V1_1,
                       ID3_V2_2, ID3_V2_3, ID3_V2_4)
from faker.providers import BaseProvider
from mishmash.orm import Album, Track


class TagFactory(factory.Factory):
    class Meta:
        model = eyed3.id3.Tag

    title = factory.Sequence(lambda n: "Track title #{:d}".format(n))
    artist = "Artist"
    album = "Album"
    album_artist = artist
    track_num = None


class Mp3AudioFileFactory(factory.Factory):
    _TEMP_D = None
    _SAMPLE_MP3 = None

    class Meta:
        model = eyed3.mp3.Mp3AudioFile

    class Params:
        id3_version = factory.Faker("id3_version")

    @factory.lazy_attribute
    def path(obj):
        if Mp3AudioFileFactory._SAMPLE_MP3 is None:
            Mp3AudioFileFactory._SAMPLE_MP3 = \
                subprocess.run("dd if=/dev/zero bs=1MB count=10 | lame -r -",
                               shell=True, check=True, stdout=subprocess.PIPE)\
                          .stdout
            if Mp3AudioFileFactory._TEMP_D is None:
                Mp3AudioFileFactory._TEMP_D = tempfile.TemporaryDirectory()
        mp3 = tempfile.NamedTemporaryFile(dir=Mp3AudioFileFactory._TEMP_D.name,
                                          suffix=".mp3", delete=False)
        mp3.write(Mp3AudioFileFactory._SAMPLE_MP3)
        mp3.close()
        return mp3.name
    version = factory.LazyAttribute(lambda obj: obj.id3_version)

    @factory.post_generation
    def tag(obj, create, extracted, **kwargs):
        if create:
            obj.tag = extracted
            obj.tag.save(version=obj._tag_version)


class AlbumFactory(factory.Factory):
    class Params:
        num_tracks = 10
        organized = True

    class Meta:
        model = Album

    title = factory.Faker("id3_title")
    artist = factory.Faker("id3_artist")
    # FIXME: original_release_date
    # FIXME: release_date
    # FIXME: recording_date

    @factory.lazy_attribute
    def tracks(obj):
        # FIXME: use obj.organized to do ARTIST/YEAR - ALBUM
        tracks = []
        for i in range(1, obj.num_tracks + 1):
            tag = TagFactory(artist=obj.artist, album=obj.title,
                             track_num=(i, obj.num_tracks))
            mp3 = Mp3AudioFileFactory(tag=tag)
            tracks.append(Track().update(mp3))
        return tracks


class Id3Provider(BaseProvider):
    _fake = faker.Faker()
    VERSION_WEIGHTS = [(ID3_V1_0, 5), (ID3_V1_1, 15),
                       (ID3_V2_2, 5), (ID3_V2_3, 60), (ID3_V2_4, 40)]

    def id3_version(self):
        return random.choices(
            [v for v, _ in self.VERSION_WEIGHTS],
            cum_weights=[w for _, w in self.VERSION_WEIGHTS])[0]

    def id3_title(self):
        return " ".join(self._fake.words(random.randint(1, 5)))

    def id3_artist(self):
        return " ".join(self._fake.words(random.randint(1, 3)))

    def id3_tag(self, **kwargs):
        return TagFactory(**kwargs)


factory.Faker.add_provider(Id3Provider)
