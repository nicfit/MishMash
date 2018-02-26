from mishmash.playlist import Playlist, Iterator


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


def test_Iterator_next():
    pl = Playlist("The Black Angels", range(50))
    assert len(pl) == 50

    piter = Iterator(pl)
    vals = [piter.next() for _ in range(55)]
    assert vals == [i for i in range(50)] + ([None] * 5)

    piter = Iterator(pl)
    pl.reverse()
    vals = [piter.next() for _ in range(55)]
    assert vals == list(reversed([i for i in range(50)])) + [None] * 5

    # No item iteration
    piter = Iterator(Playlist("Social Distortion"))
    assert [piter.next() for _ in range(20)] == [None] * 20


def test_Iterator_prev():
    pl = Playlist("Film School", range(5))
    piter = Iterator(pl)
    assert piter.prev() == None

    piter = Iterator(pl, first=len(pl))
    assert piter.prev() == 3
    assert piter.prev() == 2
    assert piter.prev() == 1
    assert piter.prev() == 0
    assert piter.prev() is None
    assert piter.prev() is None
    assert piter.prev() is None
    assert piter.next() == 0
    assert piter.next() == 1
    assert piter.next() == 2
    assert piter.next() == 3
    assert piter.next() == 4
    assert piter.next() is None


def test_Iterator_first():
    piter = Iterator(Playlist("Skinless"))
    assert piter.prev() == None
    assert piter.next() == None

    pl = Playlist("Obituary", range(5))

    piter = Iterator(pl)
    assert piter.prev() == None
    assert piter.next() == 0

    piter = Iterator(pl, first=0)
    assert piter.prev() == None
    assert piter.next() == 0

    piter = Iterator(pl, first=1)
    assert piter.next() == 1
    assert piter.prev() == 0
    assert piter.next() == 1
    assert piter.next() == 2
    assert piter.next() == 3
    assert piter.prev() == 2
    assert piter.next() == 3
    assert piter.next() == 4
    assert piter.next() == None
    assert piter.prev() == 4


def test_Iterator_repeat():
    pl = Playlist("Memories Remain", range(5))

    piter = Iterator(pl, repeat=False)
    assert piter.prev() == None
    assert piter.next() == 0
    assert piter.next() == 1
    assert piter.next() == 2
    assert piter.next() == 3
    assert piter.next() == 4
    assert piter.next() is None

    piter = Iterator(pl, repeat=True)
    assert piter.next() == 0
    assert piter.next() == 1
    assert piter.next() == 2
    assert piter.next() == 3
    assert piter.next() == 4
    assert piter.next() == 0
    assert piter.next() == 1
    assert piter.prev() == 0
    assert piter.prev() == 4

    piter = Iterator(pl, repeat=True)
    assert piter.prev() == 4
    assert piter.next() == 0
    assert piter.prev() == 4
    assert piter.prev() == 3
    assert piter.prev() == 2
    assert piter.next() == 3
    assert piter.prev() == 2
    assert piter.next() == 3
    assert piter.next() == 4

    pl = Playlist("Carcass", range(50))
    assert len(pl) == 50

    piter = Iterator(pl, repeat=True)
    vals = [piter.next() for _ in range(55)]
    assert vals == [i for i in range(50)] + list(range(5))

    piter = Iterator(pl, repeat=True)
    pl.reverse()
    vals = [piter.next() for _ in range(55)]
    assert vals == list(reversed([i for i in range(50)])) + list(reversed(range(45, 50)))

