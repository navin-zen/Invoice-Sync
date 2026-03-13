"""
Our customization of Django's Detail View. This view uses UUID instead of
PK to lookup to the object.
"""

from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView, UpdateView


class UuidDetailView(DetailView):
    pk_url_kwarg = None
    slug_field = slug_url_kwarg = "uuid"


class UuidUpdateView(UpdateView):
    pk_url_kwarg = None
    slug_field = slug_url_kwarg = "uuid"


class UuidDeleteView(DeleteView):
    pk_url_kwarg = None
    slug_field = slug_url_kwarg = "uuid"
