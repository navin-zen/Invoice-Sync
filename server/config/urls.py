from cz_utils.application.faviconurls import urlpatterns as favicon_urlpatterns
from cz_utils.application.urls import urlpatterns as common_urlpatterns
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path("invoicing/", include("invoicing.urls", namespace="invoicing")),
    path("e/", RedirectView.as_view(pattern_name="invoicing:home", permanent=False)),
    path("", RedirectView.as_view(pattern_name="invoicing:home", permanent=False)),
]

urlpatterns += common_urlpatterns
urlpatterns += favicon_urlpatterns
