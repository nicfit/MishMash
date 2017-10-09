from .factories import EpFactory


def test_sync():
    ep = EpFactory(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2,
                   track_titles=("Tide", "You Gotta Have Someone"))
    # FIXME: sync and test
