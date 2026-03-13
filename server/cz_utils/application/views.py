import logging
import os
import subprocess
import textwrap
import time

import django.utils.timezone
import requests
import xlsxwriter
from django.contrib import auth
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import mail_admins
from django.http import Http404, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView, TemplateView, View

from cz_utils.pusher import new_channel, pusher, trigger_progress
from cz_utils.utils import get_client_ip
from cz_utils.xlsxwriter_utils import Row, get_xlsxwriter_options
from cz_utils.xlsxwriter_views import XlsxResponseMixin

logger = logging.getLogger(__name__)


class SuccessView(View):
    """
    A view that returns the string 'SUCCESS'.

    The URL for this view is returned as the success url in some FormView
    classes when invoked from AJAX. The AJAX caller can know that the form
    processing is successful and take appropriate action.
    """

    def get(self, request, *args, **kwargs):
        return HttpResponse("SUCCESS", content_type="text/plain")


class UserDetailsView(View):
    """
    Details of the user making the required

    Useful to debug views that authenticate over fancy headers.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            user_from_backend = auth.authenticate(request=request)
            if user_from_backend and user_from_backend.is_authenticated:
                request.user = user_from_backend
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        authenticated = request.user and request.user.is_authenticated
        if authenticated:
            user = {
                "pk": request.user.pk,
                "email": request.user.email,
                "username": request.user.username,
            }
        else:
            user = None
        details = {
            "authenticated": authenticated,
            "user": user,
        }
        return JsonResponse(details)


class TestAsyncTaskView(View):
    """
    A view that invokes an asynchronous task.
    """

    def get(self, request, *args, **kwargs):
        logger.info("TestAsyncTaskView")
        from .async_tasks import debug_task  # This import is a bit slow, so we import here

        debug_task("This", "is", "a", "test", 34579)
        return HttpResponse("SUCCESS", content_type="text/plain")


class TestFargateAsyncTaskView(View):
    """
    A view that invokes an asynchronous task on AWS Fargate.
    """

    def get(self, request, *args, **kwargs):
        logger.info("TestFargateAsyncTaskView")
        from cz_utils import tasks

        tasks.fargate_debug_task("This", "is", "a", "test", 34579)
        return HttpResponse("SUCCESS", content_type="text/plain")


class TestCeleryAsyncTaskView(View):
    """
    A view that invokes a Celery asynchronous task.
    """

    def get(self, request, *args, **kwargs):
        logger.info("TestCeleryAsyncTaskView")
        from cz_utils import tasks

        tasks.debug_task.delay("This", "is", "a", "test", 34579)
        return HttpResponse("SUCCESS", content_type="text/plain")


class TestCelerySnsAsyncTaskView(View):
    """
    A view that invokes an asynchronous task.

    It uses Celery for local development and AWS SNS task on Lambda.
    """

    def get(self, request, *args, **kwargs):
        logger.info("TestCelerySnsAsyncTaskView")
        from cz_utils import tasks

        tasks.celery_aws_debug_task("This", "is", "a", "test", 34579)
        return HttpResponse("SUCCESS", content_type="text/plain")


class LogHeadersView(View):
    """
    A view that logs all HTTP Headers that it has received.
    """

    def get(self, request, *args, **kwargs):
        logger.info("LogHeadersView Begin")
        for key, value in request.META.items():
            logger.info(f"{key} - {value}")
        logger.info("LogHeadersView End")
        return HttpResponse("SUCCESS", content_type="text/plain")


class LogEnvironmentView(View):
    """
    A view that logs all environment variables
    """

    def get(self, request, *args, **kwargs):
        logger.info("LogEnvironmentView Begin")
        for key, value in os.environ.items():
            logger.info(f"{key:20} - {value}")
        logger.info("LogEnvironmentView End")
        return HttpResponse("SUCCESS", content_type="text/plain")


class TestEmailView(View):
    """
    A view that sends a test email.

    Useful for checking if the server is able to send emails.
    """

    def get(self, request, *args, **kwargs):
        now = django.utils.timezone.now()
        mail_admins(f"Test email sent at {now}", "This is a test email.", fail_silently=False)
        return HttpResponse("SUCCESS", content_type="text/plain")


class TestInternetAccessView(View):
    """
    A view that access google.com.

    Useful to check if our code has access to the internet.
    """

    def get(self, request, *args, **kwargs):
        r = requests.get("https://www.google.com")
        r.raise_for_status()
        return HttpResponse("SUCCESS", content_type="text/plain")


class PusherAuthenticationView(View):
    """
    Authenticates a JS client to acccess a Pusher channel.

    Implements the code sample provided in
    https://pusher.com/docs/authenticating_users#implementing_private_endpoints

    For the authentication process described in
    https://pusher.com/docs/authenticating_users#authentication_process
    """

    def post(self, request, *args, **kwargs):
        auth = pusher.authenticate(
            channel=request.POST.get("channel_name", ""), socket_id=request.POST.get("socket_id", "")
        )
        return JsonResponse(auth)


class PusherTestView(TemplateView):
    """
    A view to test our use of Pusher.
    """

    template_name = "cz_utils/pusher_test.html"

    @cached_property
    def pusher_channel(self):
        return self.request.GET.get("pusher_channel", "") or new_channel()

    def get(self, request, *args, **kwargs):
        from cz_utils import tasks

        tasks.pusher_test(pusher_channel=self.pusher_channel)
        return super().get(request, *args, **kwargs)


@method_decorator(cache_control(public=True, max_age=(10 * 24 * 3600)), name="dispatch")
class FaviconsView(RedirectView):
    """
    A view that redirects to favicon static files.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        try:
            filename = self.kwargs.get("filename", None)
            path = "favicons/" + filename
            return staticfiles_storage.url(path)
        except ValueError:
            raise Http404(f"Could not find favicon file: '{path}'")


class DemoLoginRedirectView(RedirectView):
    """
    Redirects user to the demo login home page with proper credentials
    filled in.
    """

    url = "/accounts/login/?cz:initial:login=demo@cloudzen.in&cz:initial:password=demo"


class RobotsTxtView(TemplateView):
    """
    Render our robots.txt
    """

    template_name = "robots.txt"
    content_type = "text/plain"


class IpAddressView(View):
    """
    Show client and server IP addresses
    """

    def get(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        server_ip = requests.get("https://api.ipify.org").text
        message = textwrap.dedent(
            """\
        Client IP Address (Your address): {}
        Server IP Address (My address): {}
        """
        ).format(client_ip, server_ip)
        logger.info(message)
        return HttpResponse(message, content_type="text/plain")


class TmpSpaceView(View):
    """
    Show list of files in /tmp and disk usage in /tmp

    Occasianally we get disk full error messages in Lambda. This view will
    help in debugging that.
    """

    def get(self, request, *args, **kwargs):
        cmd = "du -sh /tmp ; ls -lh /tmp ; exit 0"
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        return HttpResponse(output, content_type="text/plain")


class DeferredTestViewMixin(View):
    """
    This mixin is required since we override the get() method.

    We cannot put the get() method in DeferredTestView. Doing so override
    PossibleDeferredMixin.get().
    """

    def get(self, request, *args, **kwargs):
        time.sleep(3)
        pusher_channel = request.META.get("HTTP_X_PUSHER_CHANNEL", None)
        if pusher_channel:
            total = 3
            for i in range(total):
                data = {
                    "current": (i + 1),
                    "total": total,
                    "batch": 0,
                    "num_batches": 1,
                    "message": "Generating File",
                }
                trigger_progress(pusher_channel, data)
                time.sleep(2)
        response = HttpResponse("SUCCESS", content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format("success.txt")
        return response


class SamplePdfSpec(View):
    """
    Return PDF specification in JSON format

    for use with pdfmake
    """

    def get(self, request, *args, **kwargs):
        spec = {
            "pageSize": "A4",
            "pageOrientation": "landscape",
            "pageMargin": [40, 60, 40, 60],
            "watermark": {
                "text": "SAMPLE",
                "color": "black",
                "opacity": 0.3,
                "bold": True,
                "italics": False,
                "fontSize": 60,
            },
            "content": [
                {
                    "text": "Hello",
                    "style": "header",
                },
            ],
            "styles": {
                "header": {"fontSize": 18, "bold": True, "margin": [300, 0, 0, 10]},
            },
        }
        return JsonResponse(spec, json_dumps_params={"indent": None})


class SampleXlsxGenerator:
    @cached_property
    def about_xls_data(self):
        return Row(["Hello", "World", django.utils.timezone.now().isoformat()])

    def write(self, filename):
        """
        Write reconciliation output to a file.

        `filename` can be the name of a file or a BytesIO or StringIO
        object
        """
        with xlsxwriter.Workbook(filename, get_xlsxwriter_options()) as workbook:
            help_sheet = workbook.add_worksheet("About")
            self.about_xls_data.render(workbook, help_sheet, 0, 0)


class SampleXlsxView(XlsxResponseMixin, View):
    xlsx_filename = "sample.xlsx"
    cache_key = "constant"

    @cached_property
    def xlsx_generator(self):
        return SampleXlsxGenerator()
