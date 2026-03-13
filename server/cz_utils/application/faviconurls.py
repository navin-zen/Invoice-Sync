"""
URLs to serve favicon and other related files
"""

from cz_utils.url_utils import cz_url

from . import views

# FAVICON_RE is just a long string
# broken down into multiple lines
FAVICON_RE = (
    r"^"
    r"(?P<filename>"
    r"android-chrome-[0-9x]+.png|"
    r"favicon-[0-9x]+.png|"
    r"mstile-[0-9x]+.png|"
    r"favicon.ico|"
    r"manifest.json|"
    r"safari-pinned-tab.svg|"
    r"apple-touch-icon.png|"
    r"browserconfig.xml"
    r")$"
)

urlpatterns = [
    cz_url(FAVICON_RE, views.FaviconsView),
]
