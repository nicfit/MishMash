from factories import Mp3AudioFileFactory, TagFactory, AlbumFactory


def test_sync():
    album = AlbumFactory(num_tracks=3)
    print(album.title, "----", album.artist)
    #album2 = AlbumFactory(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2)
    #tags = TagFactory.create_batch(10, artist="Mikal Cronin", album="Tide 7\"")
    #import ipdb; ipdb.set_trace()
    ...
