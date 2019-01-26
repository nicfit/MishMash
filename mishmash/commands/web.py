from ..web import MISHMASH_WEB

if MISHMASH_WEB:
    import tempfile
    from ..core import Command
    from pyramid.scripts.pserve import PServeCommand

    @Command.register
    class Web(Command):
        NAME = "web"
        HELP = "MishMash web interface."

        def _initArgParser(self, parser):
            parser.add_argument("-p", "--port", type=int, default=None)

        def _run(self):
            if self.args.port:
                self.config["server:main"]["port"] = str(self.args.port)

            # pserve wants a file to open, so use the composed config.
            with tempfile.NamedTemporaryFile(mode="w", suffix=".ini") as config_file:
                self.config.write(config_file)
                config_file.flush()
                pserve = PServeCommand(["mishmash", config_file.name])
                return pserve.run()
