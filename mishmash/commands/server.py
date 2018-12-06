from multiprocessing import Process
from ..core import Command


class MishMashProc(Process):
    def __init__(self, cmd, *args, config=None):
        from ..__main__ import MishMash
        super().__init__(target=MishMash(config_obj=config).run, kwargs={"args_list": [cmd, *args]})

    def start(self):
        super().start()
        return self


@Command.register
class Server(Command):
    NAME = "server"
    HELP = "Sync, monitor, browse, etc."

    def _initArgParser(self, parser):
        super()._initArgParser(parser)

    def _run(self):
        """main"""

        info = MishMashProc("info", config=self.args.config)
        sync = MishMashProc("sync", "--no-prompt", "--monitor", config=self.args.config) \
                if self.args.config.getboolean("server:opts", "sync", fallback=True) else None
        web = MishMashProc("web", config=self.args.config) \
                if self.args.config.getboolean("server:opts", "web", fallback=True) else None

        info.start().join()
        if info.exitcode:
            raise RuntimeError(info)

        if sync:
            sync.start()
        if web:
            web.start().join(5)
            if web.exitcode is not None:
                raise RuntimeError(web)
            ...
        print("------------------------")
