import os
from urllib.parse import urlparse
from eyed3.utils import datePicker
from countrycode.countrycode import countrycode

NAME_PREFIXES = [u"the ", u"los ", u"la ", u"el "]


def splitNameByPrefix(s):
    s_lower = s.lower()
    for prefix in NAME_PREFIXES:
        if s_lower.startswith(prefix):
            return (s[len(prefix):], s[0:len(prefix.rstrip())])
    return (s, None)


def sortByDate(things, prefer_recording_date=False):
    # XXX: Why just just make Album types sortable by intregating this
    def _sortkey(a):
        return datePicker(a, prefer_recording_date=prefer_recording_date) or 0
    return sorted(things, key=_sortkey)


def normalizeCountry(country_str, target="iso3c", title_case=False):
    """Return a normalized name/code for country in ``country_str``.
    The input can be a code or name, the ``target`` determines output value.
    3 character ISO code is the default (iso3c), 'country_name', and 'iso2c'
    are common also. See ``countrycode.countrycode`` for details and other
    options. Raises ``ValueError`` if the country is unrecognized."""
    iso2 = "iso2c"
    iso3 = "iso3c"
    raw = "country_name"

    if country_str is None:
        return u''

    if len(country_str) == 2:
        cc = countrycode(country_str.upper(), origin=iso2, target=target)
        if not cc:
            cc = countrycode(country_str, origin=raw, target=target)
    elif len(country_str) == 3:
        cc = countrycode(country_str.upper(), origin=iso3, target=target)
        if not cc:
            cc = countrycode(country_str, origin=raw, target=target)
    else:
        cc = countrycode(country_str, origin=raw, target=target)

    # Still need to validate because origin=raw will return whatever is
    # input if not match is found.
    cc = countrycode(cc, origin=target, target=target) if cc else None
    if not cc:
        raise ValueError("Country not found: %s" % (country_str))

    return cc.title() if title_case else cc


def commonDirectoryPrefix(*args):
    return os.path.commonprefix(args).rpartition(os.path.sep)[0]


def mostCommonItem(lst):
    """Choose the most common item from the list, or the first item if all
    items are unique."""
    # This elegant solution from: http://stackoverflow.com/a/1518632/1760218
    lst = [l for l in lst if l]
    if lst:
        return max(set(lst), key=lst.count)
    else:
        return None


def safeDbUrl(db_url):
    """Obfuscates password from a database URL."""
    url = urlparse(db_url)
    return db_url.replace(url.password, "****") if url.password else db_url
