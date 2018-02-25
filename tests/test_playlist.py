from mishmash.playlist import Playlist


def test_Playlist_MutableSequence():
    pl = Playlist("Swiz")
    assert not pl
    assert pl.name == "Swiz"

    pl.append("1")
    pl += ["2", "3"]
    assert list(pl) == [str(n) for n in range(1, 4)]
    pl.insert(0, "0")
    assert list(pl) == [str(n) for n in range(0, 4)]
    pl.insert(3, "2.5")
    assert len(pl) == 5
    pl.remove("2.5")
    assert list(pl) == [str(n) for n in range(0, 4)]
    assert pl.count("3") == 1

    assert pl.pop(0) == "0"
    assert list(pl) == [str(n) for n in range(1, 4)]

    pl.reverse()
    assert list(pl) == list(reversed([str(n) for n in range(1, 4)]))

    assert pl.index("2") == 1

    pl.clear()
    assert not pl
    assert not pl._data
    assert pl.name == "Swiz"

    assert pl.current == -1


def test_Playlist_getNext():
    pl = Playlist("The Black Angels", range(50))
    assert len(pl) == 50

    vals = [pl.getNext() for _ in range(55)]
    assert vals == [i for i in range(50)] + ([None] * 5)

    pl.reset()
    pl.reverse()
    vals = [pl.getNext() for _ in range(55)]
    assert vals == list(reversed([i for i in range(50)])) + [None] * 5

    # No item iteration
    pl = Playlist("Social Distortion")
    assert [pl.getNext() for _ in range(20)] == [None] * 20


def test_Playlist_getPrevious():
    pl = Playlist("Film School", range(5))
    assert pl.getPrevious() == 4
    assert pl.getPrevious() == 3
    assert pl.getPrevious() == 2
    assert pl.getPrevious() == 1
    assert pl.getPrevious() == 0
    import ipdb; ipdb.set_trace();
    ...
    assert pl.getPrevious() is None
    #print(pl.getPrevious())
    #print(pl.getPrevious())
    #print(pl.getPrevious())
    #print(pl.getPrevious())
