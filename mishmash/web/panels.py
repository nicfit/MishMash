import random
from pyramid_layout.panel import panel_config
from ..__about__ import __version__, __years__, __project_name__
from .. import orm


@panel_config(name='navbar',
              renderer='mishmash.web:templates/panels/navbar.pt')
def navbar(context, request):
    # XXX: has not been needed for a while, leaving as a panel in the case it is again.
    return {}


@panel_config(name='footer')
def footer(context, request):
    return f"""
<footer class="text-muted">
  <div class="container">
    <p class="float-right">
      <a href="#">Back to top</a>
    </p>
    <p><br/></p>
    <p align='right'>{__project_name__} {__version__} &copy; {__years__}</p>
  </div>
</footer>
"""


@panel_config(name='album_cover')
def album_cover(context, request, album, size=None, link=False):
    front_covers = [img for img in album.images
                        if img.type == orm.Image.FRONT_COVER_TYPE]
    cover_id = random.choice(front_covers).id if front_covers else "default"
    cover_url = request.route_url("images.covers", id=cover_id)
    width = str(size or "100%")
    height = str(size or "100%")

    panel = (
        u"<img class='shadow' width='%s' height='%s' src='%s' title='%s'/>" %
        (width, height, cover_url, "%s - %s" % (album.artist.name, album.title))
    )

    if link:
        panel = u"<a href='%s'>%s</a>" % \
                (request.route_url('album', id=album.id), panel)

    return panel
