import random
import collections.abc


class Playlist(collections.abc.MutableSequence):

    def __init__(self, name, pl=None):
        self.name = name
        self._data = list(pl or [])
        self.shuffle = False
        self.repeat = False
        #self.reset()
        self._shuffle_history = []

    '''
    def reset(self, current=0, seed=None):
        # Queued indexes where the beginning of the list is the next source
        self._queue = []
        self._shuffle_hist = []
    '''

    '''
    @property
    def current(self):
        return self._curr_index

    @current.setter
    def current(self, i):
        if 0 <= i < len(self):
            self._curr_index = i
        else:
            raise ValueError("index out of range")
    '''

    @property
    def repeat(self):
        return self._repeat

    @repeat.setter
    def repeat(self, enabled):
        self._repeat = bool(enabled)

    @property
    def shuffle(self):
        return self._shuffle

    @shuffle.setter
    def shuffle(self, enabled):
        self._shuffle = bool(enabled)
        self._shuffle_hist = []

    # --- Iterator interfaces --- #
    def getNext(self):
        if not len(self):
            return None

        if self._queue:
            self.current = self._queue.pop(0)
        elif self.shuffle:
            alls = set(range(len(self)))
            history = set(self._shuffle_history)
            choices = list(alls.difference(history))
            if not choices and self.repeat:
                self.reset()
                # Return with new choices
                return self.getNext()
            elif not choices:
                next = None
            else:
                self.current = random.choice(choices)
                self._shuffle_history.append(self.current)
        elif self.current == self._OVER_IDX:
            if not self.repeat:
                return None
            self.reset(0)
        elif self.current in (self.INIT_IDX, self._UNDER_IDX):
            self.current = 0

        next = self[self.current]
        self.current += 1
        return next

    def hasNext(self):
        if not len(self):
            return False
        return (self._queue or self.repeat or
                self.current + 1 < len(self) or
                (self.shuffle and len(self._shuffle_hist) <= len(self)))

    def getPrevious(self):
        #import ipdb; ipdb.set_trace();
        ...
        if not len(self):
            return None

        if self.shuffle:
            if not self._shuffle_hist:
                return None
            else:
                prev_idx = self._shuffle_hist.pop()
                if (prev_idx == self.current) and self._shuffle_hist:
                    prev_idx = self._shuffle_hist.pop()
                self.current = prev_idx
        elif self.current == self._UNDER_IDX:
            if not self.repeat:
                return None
            self.reset(len(self) - 1)

        if self.current in (self._OVER_IDX, self.INIT_IDX):
            self.current = len(self) - 1

        prev = self[self.current]
        self.current = max(self.current - 1, 0)
        return prev

    def hasPrevious(self):
        if not len(self):
            return False
        return (self.shuffle and len(self._shuffle_hist) > 0) or \
                self.repeat or self.current > 0

    # --- MutableSequence interface --- #
    def __delitem__(self, i):
        '''
        # Adjust index pointers
        if i < self.current:
            self.current -= 1

        if i in self._queue:
            self._queue.remove(i)
        for q in range(len(self._queue)):
            if i < self._queue[q]:
                self._queue[q] -= 1
        '''

        if self.shuffle and self._shuffle_hist:
            if i in self._shuffle_hist:
                self._shuffle_hist.remove(i)
            for h in range(len(self._shuffle_hist)):
                if i < self._shuffle_hist[h]:
                    self._shuffle_hist[h] -= 1

        item = self._data.pop(i)
        return item

    def __getitem__(self, i):
        return self._data[i]

    def __len__(self):
        return len(self._data)

    def __setitem__(self, i, item):
        self._data[i] = item

    def insert(self, i, item):
        '''
        # Adjust index pointers
        if i <= self.current:
            self.current += 1
        for q in range(len(self._queue)):
            if i <= self._queue[q]:
                self._queue[q] += 1
        '''
        if self.shuffle and self._shuffle_hist:
            for h in range(len(self._shuffle_hist)):
                if i <= self._shuffle_hist[h]:
                    self._shuffle_hist[h] += 1

        self._data.insert(i, item)

    # --- Play queue interface --- #
    def hasQueue(self):
        return bool(self._queue)

    @property
    def queue(self):
        """Returns a copy of the play queue (indices)"""
        return list(self._queue)

    @queue.setter
    def queue(self, q):
        """A list of integer indexes"""
        self._queue.clear()
        self._queue.extend(q)

    def enqueue(self, idx, pos=None):
        if idx in self._queue:
            self._queue.remove(idx)

        if pos is None:
            self._queue.append(idx)
        else:
            self._queue.insert(pos, idx)

    def dequeue(self, idx):
        self._queue.remove(idx)


class Iterator:

    def __init__(self, playlist, first=None):
        self._pl = playlist
        self._UPPER = Iterator.UpperBound(playlist)
        self._LOWER = Iterator.LowerBound(playlist)
        self.reset(first=first)

    class _Bounds:
        def __init__(self, pl):
            self._pl = pl

    class LowerBound(_Bounds):
        def __eq__(self, i):
            return (i is not None) and (i < 0 if self._pl else True)

    class UpperBound(_Bounds):
        def __eq__(self, i):
            return (i is not None) and i >= len(self._pl)

    def reset(self, first=None, seed=None):
        random.seed(seed)  # None uses os.urandom() or worst-case system time
        self._ptr = max(first - 1, -1) if (first is not None) else None

    def next(self):
        if not len(self._pl):
            return None
        elif self._ptr in (None, self._LOWER):
            self._ptr = -1
        elif self._ptr == self._UPPER:
            # TODO: repeat
            return None

        self._ptr += 1
        if self._ptr == self._UPPER:
            # TODO: repeat
            return None
        item = self._pl[self._ptr]
        return item

    def prev(self):
        if not len(self._pl):
            return None
        elif self._ptr is None:
            # TODO: repeat
            return None

        self._ptr = max(self._ptr - 1, -1)
        if self._ptr in (self._LOWER, self._UPPER):
            return None
        item = self._pl[self._ptr]
        return item