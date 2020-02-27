from collections import namedtuple


def __parse_version(v):                                       # pragma: nocover
    ver, rel = v, "final"
    for c in ("a", "b", "c"):
        parsed = v.split(c)
        if len(parsed) == 2:
            ver, rel = (parsed[0], c + parsed[1])

    v = tuple((int(v) for v in ver.split(".")))
    ver_info = namedtuple("Version", "major, minor, maint, release")(
        *(v + (tuple((0,)) * (3 - len(v))) + tuple((rel,))))
    return ver, rel, ver_info


__version__ = "0.3.2"
__release_name__ = "Gareth Brown Says"
__years__ = "2013-2020"

_, __release__, __version_info__ = __parse_version(__version__)
__project_name__ = "MishMash"
__project_slug__ = "mishmash"
__pypi_name__ = "MishMash"
__author__ = "Travis Shirk"
__author_email__ = "travis@pobox.com"
__url__ = "https://github.com/nicfit/MishMash"
__description__ = "Music database and web interface."
__long_description__ = ""
__license__ = "GNU GPL v3.0"
__github_url__ = "https://github.com/nicfit/mishmash",
__version_txt__ = """
%(__name__)s %(__version__)s (C) Copyright %(__years__)s %(__author__)s
This program comes with ABSOLUTELY NO WARRANTY! See LICENSE for details.
Run with --help/-h for usage information or read the docs at
%(__url__)s
""" % (locals())
