import gettext
from pyramid_layout.layout import layout_config

_ = gettext.gettext


@layout_config(
    name='main-layout',
    template='mishmash.web:templates/layouts/main-layout.pt'
)
class AppLayout:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.home_url = request.application_url
        self.headings = []

    @property
    def page_title(self):
        return _("MishMash music!")

    def add_heading(self, name, *args, **kw):
        self.headings.append((name, args, kw))
