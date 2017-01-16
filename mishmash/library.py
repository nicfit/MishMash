from pathlib import Path


class MusicLibrary:
    def __init__(self, name, paths=None, sync=True):
        self.name = name
        self.paths = paths or []
        self.sync = sync

    @staticmethod
    def fromConfig(config):
        all_paths = []
        paths = config.get("paths")
        if paths:
            paths = paths.split("\n")
            for p in [Path(p).expanduser() for p in paths]:
                glob_paths = Path("/").glob(str(p.relative_to("/")))
                all_paths += [str(p) for p in glob_paths]

        return MusicLibrary(config.name.split(":", 1)[1], paths=all_paths,
                            sync=config.getboolean("sync", True))
