from .factories import EpFactory


def test_sync():
    ep = EpFactory(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2)
    # FIXME: sync and test
