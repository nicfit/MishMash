import multiprocessing

from time import time
from pathlib import Path
from itertools import chain

from inotify.adapters import Inotify
from inotify.constants import (IN_ACCESS, IN_ALL_EVENTS, IN_ATTRIB,
                               IN_CLOSE_WRITE, IN_CLOSE_NOWRITE, IN_CREATE,
                               IN_DELETE, IN_ISDIR, IN_OPEN, IN_MODIFY,
                               IN_MOVED_TO, IN_MOVED_FROM)
from nicfit import getLogger

log = getLogger(__name__)
SYNC_INTERVAL = 10


class Monitor(multiprocessing.Process):

    def __init__(self):
        self._inotify = Inotify()
        self._inotify_mask = IN_ALL_EVENTS & (~IN_ACCESS &
                                              ~IN_OPEN &
                                              ~IN_CLOSE_NOWRITE &
                                              ~IN_CLOSE_WRITE)

        self._dir_queue = multiprocessing.Queue()
        self._sync_queue = multiprocessing.Queue()
        self._watched_dirs = {}   # {lib_name: set(dirs)}

        super().__init__(target=self._main, args=(self._dir_queue,
                                                  self._sync_queue))

    def _main(self, dir_queue, sync_queue):
        next_sync_t = time() + SYNC_INTERVAL
        sync_dirs = set()

        try:
            while True:
                # Check for new directories to watch
                while not dir_queue.empty():
                    lib, path = dir_queue.get()

                    watched = (path in set(chain(*self._watched_dirs.values())))

                    if lib not in self._watched_dirs:
                        self._watched_dirs[lib] = set()
                    self._watched_dirs[lib].add(path)

                    if not watched:
                        self._inotify.add_watch(str(path), self._inotify_mask)
                        log.info(f"Watching {path} (lib: {lib}) "
                                 f"(total dirs: {len(self._watched_dirs[lib])}")

                # Process Inotify
                for event in self._inotify.event_gen():
                    if event is None:
                        break

                    (header,
                     type_names,
                     watch_path,
                     filename) = event
                    watch_path = Path(watch_path)
                    filename = Path(filename)

                    log.debug(
                        f"WD=({header.wd}) MASK=({header.mask}) "
                        f"MASK->NAMES={type_names} WATCH-PATH={watch_path} FILENAME={filename}")

                    if header.mask & (IN_ATTRIB | IN_CREATE | IN_DELETE |
                                      IN_MODIFY | IN_MOVED_TO | IN_MOVED_FROM):
                        if IN_ISDIR & header.mask and header.mask & IN_CREATE:
                            watch_path = watch_path / filename
                        elif IN_ISDIR & header.mask and header.mask & IN_DELETE:
                            self._inotify.remove_watch(str(watch_path))

                        sync_dirs.add(watch_path)

                def _reqSync(l, d):
                    if d.exists():
                        sync_queue.put((lib, d))
                        log.info(f"Requesting sync {d} (lib: {l})")

                if time() > next_sync_t:
                    for d in sync_dirs:
                        for lib in self._watched_dirs:
                            lib_paths = self._watched_dirs[lib]
                            if d in lib_paths:
                                _reqSync(lib, d)
                                if not d.exists():
                                    self._watched_dirs[lib].remove(d)
                            elif d.parent in lib_paths:
                                _reqSync(lib, d)
                                self.dir_queue.put((lib, d))

                    sync_dirs.clear()
                    next_sync_t = time() + SYNC_INTERVAL

        except KeyboardInterrupt:
            pass
        finally:
            for path in set(chain(*self._watched_dirs.values())):
                self._inotify.remove_watch(str(path))

    @property
    def dir_queue(self):
        return self._dir_queue

    @property
    def sync_queue(self):
        return self._sync_queue
