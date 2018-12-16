import time
from multiprocessing import Process
from ..core import Command, CommandError


class MishMashProc(Process):
    def __init__(self, cmd, *args, config=None):
        from ..__main__ import MishMash
        self._cmd = cmd
        super().__init__(target=MishMash(config_obj=config).run, kwargs={"args_list": [cmd, *args]})

    def __str__(self):
        if self.exitcode is None:
            return f"`mishmash {self._cmd}` <running>"
        else:
            return f"`mishmash {self._cmd}` <stopped[{self.exitcode}]>"

    def start(self):
        super().start()
        return self

    def join(self, timeout=None, check=False) -> None:
        super().join(timeout)
        if check:
            if self.exitcode:
                raise CommandError(self)


@Command.register
class Server(Command):
    NAME = "server"
    HELP = "Sync, monitor, browse, etc."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _initArgParser(self, parser):
        super()._initArgParser(parser)

    def _run(self):
        """main"""
        subprocs = []

        info = MishMashProc("info", config=self.args.config)
        sync = MishMashProc("sync", "--no-prompt", "--monitor", config=self.args.config) \
                if self.args.config.getboolean("server", "sync", fallback=True) else None
        web = MishMashProc("web", config=self.args.config) \
                if self.args.config.getboolean("server", "web", fallback=True) else None

        info.start().join(check=True)
        
        if sync:
            subprocs.append(sync)
            sync.start()

        if web:
            subprocs.append(web)
            web.start()

        try:
            while True:
                for proc in subprocs:

                    proc.join(1)
                    if proc.exitcode is not None:
                        raise CommandError(proc)

                time.sleep(5)
        finally:
            for proc in subprocs:
                proc.kill()
