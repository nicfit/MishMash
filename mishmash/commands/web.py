from ..web import MISHMASH_WEB

if MISHMASH_WEB:
    import tempfile
    from nicfit import command
    from ..core import Command
    from pyramid.scripts.pserve import PServeCommand

    @command.register
    class Web(Command):
        NAME = "web"
        HELP = "MishMash web interface."

        def _run(self):
            # pserve wants a file to open, so use the *composed* config.
            with tempfile.NamedTemporaryFile(mode="w") as config_file:
                self.config.write(config_file)
                config_file.flush()
                argv = ["mishmish", config_file.name]
                pserve = PServeCommand(argv)
                return pserve.run()
