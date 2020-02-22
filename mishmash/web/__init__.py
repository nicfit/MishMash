try:
    import pyramid                                                  # noqa: F401
    MISHMASH_WEB = True
except ImportError:
    MISHMASH_WEB = False
else:
    from pyramid.config import Configurator
    from zope.sqlalchemy import register as zope_tranaction_register

    from .. import database
    from ..config import Config

    def _configure(settings, DBSession):
        config = Configurator(settings=settings)

        config.include('pyramid_chameleon')
        config.include('pyramid_layout')

        def _DBSession(request):
            return DBSession()
        config.add_request_method(_DBSession, name="DBSession", reify=True)

        config.add_static_view('static', 'mishmash.web:static',
                               cache_max_age=3600)

        config.add_route('all_artists', '/artists')
        config.add_route('all_albums', '/albums')
        config.add_route('artist', '/artist/{id:\d+}')  # noqa: W605
        config.add_route('images.covers', '/images/covers/{id:\d+|default}')  # noqa: W605
        config.add_route('images.artist', '/images/artist/{id:\d+|default}')  # noqa: W605
        config.add_route('home', '/')
        config.add_route('search', '/search')
        config.add_route('new_music', '/new')
        config.add_route('album', '/album/{id:\d+}')  # noqa: W605

        config.scan(".panels")
        config.scan(".layouts")
        config.scan(".views")

        return config

    def main(global_config, **main_settings):
        app_config = Config(global_config["__file__"])
        app_config.read()
        mm_settings = app_config["mishmash"]

        engine_args = dict(database.DEFAULT_ENGINE_ARGS)
        pfix, plen = "sqlalchemy.", len("sqlalchemy.")
        # Strip prefix and remove url value
        sql_ini_args = {
                name[plen:]: mm_settings[name]
                for name in mm_settings
                if name.startswith(pfix) and not name.endswith(".url")
        }
        engine_args.update(sql_ini_args)

        (engine,
         SessionMaker,
         connection) = database.init(app_config.db_url, engine_args=engine_args, scoped=True,
                                     trans_mgr=zope_tranaction_register)

        pyra_config = _configure(main_settings, SessionMaker)
        return pyra_config.make_wsgi_app()
