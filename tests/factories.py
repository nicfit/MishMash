import random
import tempfile
import subprocess
from enum import Enum
from pathlib import Path

import faker
import factory
import factory.fuzzy
import eyed3.id3
import eyed3.mp3
from eyed3.core import Date, AudioFile, LP_TYPE, EP_TYPE
from eyed3.id3 import (ID3_V1_0, ID3_V1_1,
                       ID3_V2_2, ID3_V2_3, ID3_V2_4)
from faker.providers import BaseProvider
from mishmash.orm import Album, Track, Library

EP_SIZE = (2, 9)
LP_SIZE = (10, 20)


class DirectoryStructure(Enum):
    NONE = 0
    PREFERRED = 1

    def structuredPath(self, file):
        assert isinstance(file, AudioFile)
        tag = file.tag
        assert tag.file_info.name == file.path

        tmp_d = Path(Mp3AudioFileFactory._TEMP_D.name)
        assert tmp_d.exists()

        if self == DirectoryStructure.NONE:
            return file.path
        else:
            assert self == DirectoryStructure.PREFERRED
            return tmp_d / f"{tag.artist}" / \
                   f"{tag.original_release_date} - {tag.album}" / \
                   f"{tag.artist} - {tag.track_num[0]} - {tag.title}"

    def apply(self, file):
        curr_path = Path(file.path)
        new_path = self.structuredPath(file)

        if not new_path.parent.exists():
            new_path.parent.mkdir(parents=True)

        if curr_path.name != new_path.name:
            file.rename(str(new_path))


class TagFactory(factory.Factory):
    class Params:
        id3_version = factory.Faker("id3_version")

    class Meta:
        model = eyed3.id3.Tag

    title = factory.Sequence(lambda n: "Track title #{:d}".format(n))
    artist = "Artist"
    album = "Album"
    album_artist = artist
    track_num = None

    @classmethod
    def create_batch(cls, size, version, track_titles=None, **kwargs):
        tags = super().create_batch(size, **kwargs)
        for i, t in enumerate(tags, 1):
            t.version = version
            if track_titles and i <= len(track_titles):
                t.title = track_titles[i - 1]
            t.track_num = (i, size)
        return tags


class Mp3AudioFileFactory(factory.Factory):
    _TEMP_D = None
    _SAMPLE_MP3 = subprocess.run("dd if=/dev/zero bs=1MB count=10 | lame -r -",
                                 shell=True, check=True,
                                 stdout=subprocess.PIPE).stdout

    version = factory.LazyAttribute(lambda obj: obj.id3_version)

    class Meta:
        model = eyed3.mp3.Mp3AudioFile

    class Params:
        id3_version = factory.Faker("id3_version")

    @factory.lazy_attribute
    def path(obj):
        if Mp3AudioFileFactory._TEMP_D is None:
            Mp3AudioFileFactory._TEMP_D = tempfile.TemporaryDirectory()
        mp3 = tempfile.NamedTemporaryFile(dir=Mp3AudioFileFactory._TEMP_D.name,
                                          suffix=".mp3", delete=False)
        mp3.write(Mp3AudioFileFactory._SAMPLE_MP3)
        mp3.close()
        return mp3.name

    @factory.post_generation
    def tag(obj, create, extracted, **kwargs):
        if create:
            obj.tag = extracted
            obj.tag.save(version=obj._tag_version)


class AlbumFactory(factory.Factory):
    class Params:
        num_tracks = factory.fuzzy.FuzzyInteger(*LP_SIZE)
        dir_structure = DirectoryStructure.PREFERRED
        id3_version = factory.Faker("id3_version")
        track_titles = []

    class Meta:
        model = Album

    type = LP_TYPE
    title = factory.Faker("id3_title")
    artist = factory.Faker("id3_artist")
    original_release_date = factory.Faker("id3_date")
    # TODO: Must me >= original_release_date
    release_date = original_release_date

    @factory.lazy_attribute
    def tracks(obj):
        tags = TagFactory.create_batch(obj.num_tracks, obj.id3_version,
                                       obj.track_titles,
                                       artist=obj.artist,
                                       album=obj.title)
        assert len(tags) == obj.num_tracks
        assert len(set([t.track_num[0] for t in tags])) == obj.num_tracks
        assert all([bool(t.album == obj.title) for t in tags])
        assert all([bool(t.artist == obj.artist) for t in tags])

        tracks = []
        for t in tags:
            t.original_release_date = obj.original_release_date
            if obj.id3_version[0] != 1:
                # TODO: allow for different, but greater than, value
                t.release_date = obj.original_release_date

            mp3 = Mp3AudioFileFactory(tag=t)
            assert hasattr(t, "file_info") and t.file_info.name,\
                        "Tag is not attached to a file"

            obj.dir_structure.apply(mp3)
            tracks.append(Track().update(mp3))

        return tracks


class EpFactory(AlbumFactory):
    class Params:
        num_tracks = factory.fuzzy.FuzzyInteger(*EP_SIZE)
    type = EP_TYPE


class LibraryFactory(factory.Factory):

    class Meta:
        model = Library

    name = factory.Faker("id3_title")
    last_sync = None


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

    def id3_date(self):
        d = self._fake.date_object()
        full_date = random.choices(["y", "n"], cum_weights=[15, 85]) == "y"
        return Date(year=d.year,
                    month=d.month if full_date else None,
                    day=d.day if full_date else None)

    def id3_tag(self, **kwargs):
        return TagFactory(**kwargs)


factory.Faker.add_provider(Id3Provider)
