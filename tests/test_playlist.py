import pytest
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


def test_Iterator_next_StopIteration():
    pl = Playlist("The Black Angels", range(50))
    assert len(pl) == 50

    piter = Iterator(pl, stop_iteration=True)
    vals = [piter.next() for _ in range(50)]
    assert vals == [i for i in range(50)]

    piter = Iterator(pl, stop_iteration=True)
    pl.reverse()
    vals = [piter.next() for _ in range(50)]
    assert vals == list(reversed([i for i in range(50)]))

    # No item iteration
    piter = Iterator(Playlist("Social Distortion"), stop_iteration=True)
    with pytest.raises(StopIteration):
        piter.next()


def test_Iterator_prev_StopIteration():
    pl = Playlist("Film School", range(5))
    piter = Iterator(pl, stop_iteration=True)
    with pytest.raises(StopIteration):
        assert piter.prev() == None

    piter = Iterator(pl, first=len(pl), stop_iteration=True)
    assert piter.prev() == 3
    assert piter.prev() == 2
    assert piter.prev() == 1
    assert piter.prev() == 0
    with pytest.raises(StopIteration):
        assert piter.prev() is None
    with pytest.raises(StopIteration):
        assert piter.prev() is None
    assert piter.next() == 0
    assert piter.next() == 1
    assert piter.next() == 2
    assert piter.next() == 3
    assert piter.next() == 4
    with pytest.raises(StopIteration):
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


def test_Iterator_queue():
    p = Playlist("Neat Neat Neat")
    piter = Iterator(p, stop_iteration=True)
    assert not piter.hasQueue()
    assert not len(piter.queue)

    with pytest.raises(IndexError):
        piter.queue = [0, 1, 2, 3]
    p.append("Eagle")
    p.append("Simon")
    p.append("Nate")
    p.append("Paul")
    piter.queue = [3, 2, 1, 0]
    assert piter.queue is not piter._queue
    assert piter.queue == [3, 2, 1, 0]

    assert piter.next() == "Paul"
    assert piter.next() == "Nate"
    assert piter.next() == "Simon"
    assert piter.next() == "Eagle"

    assert piter.next() == "Eagle"
    assert piter.next() == "Simon"
    assert piter.next() == "Nate"
    assert piter.next() == "Paul"
    with pytest.raises(StopIteration):
        piter.next()

    assert piter.prev() == "Paul"
    assert piter.prev() == "Nate"
    assert piter.prev() == "Simon"
    assert piter.prev() == "Eagle"
    with pytest.raises(StopIteration):
        piter.prev()

    assert piter.next() == "Eagle"
    assert piter.next() == "Simon"
    assert piter.next() == "Nate"
    assert piter.next() == "Paul"
    with pytest.raises(StopIteration):
        piter.next()


def test_enqueue():
    p = Playlist("2018 Memorial", ["Simon", "Eagle", "Nate", "Paul", "Nikko"])
    piter = Iterator(p)
    piter.enqueue(1)
    piter.enqueue(4)
    piter.enqueue(3)
    assert piter.queue == [1, 4, 3]
    piter.enqueue(4)
    assert piter.queue == [1, 3, 4]

    piter.enqueue(0, 0)
    assert piter.queue == [0, 1, 3, 4]
    piter.enqueue(2, 1)
    assert piter.queue == [0, 2, 1, 3, 4]

    piter.dequeue(4)
    assert piter.queue == [0, 2, 1, 3]
    piter.dequeue(2)
    piter.dequeue(0)
    assert piter.queue == [1, 3]
