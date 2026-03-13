"""
Views related to data-sources
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from invoicing.utils.datasource.databases_old import CONNECTION_PARAMS, postgresql_connect

__all__ = ("CheckDatabaseConnection",)


@method_decorator(csrf_exempt, name="dispatch")
class CheckDatabaseConnection(View):
    def post(self, request, *args, **kwargs):
        connection_kwargs = {k: self.request.GET.get(k) for k in CONNECTION_PARAMS}
        status = postgresql_connect(**connection_kwargs)
        return JsonResponse({"status": status})


