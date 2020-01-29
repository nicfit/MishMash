""""""
from nicfit.console.ansi import Fg
from eyed3.utils.prompt import prompt, parseIntList
from .orm import Artist


def selectArtist(heading, choices=None, multiselect=False, allow_create=True):
    color = Fg.green
    artist = None
    name = None
    menu_num = 0

    if heading:
        print(heading)

    while artist is None:
        if choices:
            name = choices[0].name
            for menu_num, a in enumerate(choices, start=1):
                print("   %d) %s" % (menu_num + 1, a.origin()))

            if not multiselect:
                if allow_create:
                    menu_num += 1
                    print("   %d) Enter a new artist" % menu_num)

                choice = prompt("Which artist", type_=int,
                                choices=range(1, menu_num + 1))
                choice -= 1
                if choice < len(choices):
                    artist = choices[choice]
                # Otherwise fall through to select artist below
            else:
                def _validate(_resp):
                    try:
                        _ints = [_i for _i in parseIntList(_resp)
                                    if _i in range(1, menu_num + 1)]
                        return bool(_ints)
                    except Exception:
                        return False

                resp = prompt(color("Choose one or more artists"),
                              validate=_validate)
                artists = []
                for choice in [i - 1 for i in parseIntList(resp)]:
                    artists.append(choices[choice])
                # XXX: blech, returning a list here and a single value below
                return artists

        if artist is None:
            artist = promptArtist(None, name=name)
            if choices:
                if not Artist.checkUnique(choices + [artist]):
                    print(Fg.red("Artist entered is not unique, try again..."))
                    artist = None

    return artist


def promptArtist(text, name=None, default_name=None, default_city=None,
                 default_state=None, default_country=None, artist=None):
    if text:
        print(text)

    if name is None:
        name = prompt(Fg.green("Artist name"), default=default_name)

    origin = {}
    for o in ("city", "state", "country"):
        origin["origin_%s" % o] = prompt("   %s" % Fg.green(o.title()),
                                         default=locals()["default_%s" % o],
                                         required=False)

    if not artist:
        artist = Artist(name=name, **origin)
    else:
        artist.name = name
        for o in origin:
            setattr(artist, o, origin[o])
    return artist
