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
from mishmash.core import EP_MAX_SIZE_HINT
from mishmash.orm import Artist, Album, Track, Library

EP_SIZE = (2, EP_MAX_SIZE_HINT)
LP_SIZE = (EP_MAX_SIZE_HINT + 1, 24)


class DirectoryStructure(Enum):
    NONE = 0
    PREFERRED = 1

    def structuredPath(self, file):
        assert isinstance(file, AudioFile)
        tag = file.tag
        assert tag.file_info.name == file.path

        if self == DirectoryStructure.NONE:
            return file.path
        else:
            assert self == DirectoryStructure.PREFERRED
            return Path().joinpath(
                f"{tag.artist}",
                f"{tag.original_release_date} - {tag.album}",
                f"{tag.artist} - {tag.track_num[0]} - {tag.title}")

    def apply(self, *files, root_dir="./"):
        root_dir = Path(root_dir)
        for file in files:
            curr_path = Path(file.path)
            new_path = root_dir / self.structuredPath(file)

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
    album_artist = None
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

    class Meta:
        model = eyed3.mp3.Mp3AudioFile

    class Params:
        id3_version = factory.Faker("id3_version")
        temp_dir = None

    @factory.lazy_attribute
    def path(obj):
        tmp_dir = str(obj.temp_dir) if obj.temp_dir \
                                    else Mp3AudioFileFactory.getTempDir()
        mp3 = tempfile.NamedTemporaryFile(dir=str(tmp_dir),
                                          suffix=".mp3", delete=False)
        mp3.write(Mp3AudioFileFactory._SAMPLE_MP3)
        mp3.close()
        return mp3.name

    @factory.post_generation
    def tag(obj, create, extracted, **kwargs):
        if create:
            obj.tag = extracted
            obj.tag.save(version=obj.tag.version)

    @classmethod
    def getTempDir(cls):
        if cls._TEMP_D is None:
            cls._TEMP_D = tempfile.TemporaryDirectory()
        return Path(cls._TEMP_D.name)


class ArtistFactory(factory.Factory):
    class Meta:
        model = Artist


class AlbumFactory(factory.Factory):
    class Params:
        num_tracks = factory.fuzzy.FuzzyInteger(*LP_SIZE)
        dir_structure = DirectoryStructure.PREFERRED
        id3_version = factory.Faker("id3_version")
        track_titles = []
        temp_dir = None

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
            t.album_type = obj.type
            t.original_release_date = obj.original_release_date
            if obj.id3_version[0] != 1:
                # TODO: allow for different, but greater than, values
                t.release_date = obj.original_release_date

            mp3 = Mp3AudioFileFactory(tag=t, temp_dir=obj.temp_dir)
            assert hasattr(t, "file_info") and t.file_info.name,\
                        "Tag is not attached to a file"

            track = Track().update(mp3)
            track._mp3_file = mp3
            track.artist = ArtistFactory(name=obj.artist)
            # Note, cannot call AlbumFactory here as calling this function is
            # required to do so.
            track.album = Album(title=obj.title, type=obj.type,
                                artist=obj.artist,
                                original_release_date=obj.original_release_date,
                                release_date=obj.release_date)
            tracks.append(track)

        return tracks


class EpFactory(AlbumFactory):
    class Params:
        num_tracks = factory.fuzzy.FuzzyInteger(*EP_SIZE)
    type = EP_TYPE


class LpFactory(AlbumFactory):
    class Params:
        num_tracks = factory.fuzzy.FuzzyInteger(*LP_SIZE)
    type = LP_TYPE


class LibraryFactory(factory.Factory):

    class Meta:
        model = Library

    name = factory.Faker("id3_title")
    last_sync = None

    '''
    def defaultDir(self, tmpdir):
        self._tmdir = tmpdir

    def addEp(self, *args, **kwargs):
        # TODO
        # TODO: use self._tmpdir if set
        return self
    '''


class Id3Provider(BaseProvider):
 _fake = faker.Faker()
 V1_VERSION_WEIGHTS = [(ID3_V1_0, 5), (ID3_V1_1, 15)]
 V2_VERSION_WEIGHTS = [(ID3_V2_2, 5), (ID3_V2_3, 60), (ID3_V2_4, 40)]
 VERSION_WEIGHTS = V1_VERSION_WEIGHTS + V2_VERSION_WEIGHTS

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
