import time
import subprocess

from multiprocessing import Process
from ..core import Command, CommandError


class MishMashProc(Process):
    def __init__(self, cmd, *args, config=None):
        self._cmd = cmd
        super().__init__(target=MishMashProc._entryPoint, args=[config, cmd, *args])

    @staticmethod
    def _entryPoint(config, cmd, *args):
        from ..__main__ import MishMash
        return MishMash(config_obj=config).run(args_list=[cmd, *args])

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


class UnsonicProc:
    def __init__(self, config):
        self._config = config
        self._unsonic = None
        self.exitcode = None

    def start(self):
        self._unsonic = subprocess.Popen([
            "unsonic", "--config", self._config, "serve"
        ])
        return self

    def join(self, timeout=None, check=False) -> None:
        if self.exitcode is not None:
            return

        try:
            self._unsonic.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.exitcode = None
            return

        self.exitcode = self._unsonic.returncode
        if check and self.exitcode is not None and self.exitcode:
            raise CommandError(self)

    def kill(self):
        self._unsonic.kill()


@Command.register
class Server(Command):
    NAME = "server"
    HELP = "Sync, monitor, browse, etc."

    def _run(self):
        """main"""
        all_procs = []

        # `mishmash info`: tests the config and get banner and info.
        MishMashProc("info", config=self.args.config).start().join(check=True)

        sync = MishMashProc("sync", "--no-prompt", "--monitor", config=self.args.config) \
                if self.args.config.getboolean("server", "sync", fallback=True) else None
        web = MishMashProc("web", config=self.args.config) \
                if self.args.config.getboolean("server", "web", fallback=True) else None
        unsonic = self._createUnsonic()

        for p in (sync, web, unsonic):
            if p:
                all_procs.append(p)
                p.start()

        try:
            while True:
                for proc in all_procs:
                    proc.join(1, check=True)
                time.sleep(5)
        finally:
            for proc in all_procs:
                proc.kill()

    def _createUnsonic(self):
        if self.args.config.getboolean("server", "unsonic", fallback=False):
            cfg_file = self.args.config.get("unsonic", "config")
            return UnsonicProc(cfg_file)
