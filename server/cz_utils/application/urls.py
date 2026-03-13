"""
Utility URLs
"""

from cz_utils.url_utils import cz_url

from . import views

app_name = "cz_utils"
urlpatterns = [
    cz_url(r"^test-async-task/$", views.TestAsyncTaskView),
    cz_url(r"^test-celery-task/$", views.TestCeleryAsyncTaskView),
    cz_url(r"^test-celery-aws-task/$", views.TestCelerySnsAsyncTaskView),
    cz_url(r"^test-fargate-aws-task/$", views.TestFargateAsyncTaskView),
    cz_url(r"^log-headers/$", views.LogHeadersView),
    cz_url(r"^log-environment/$", views.LogEnvironmentView),
    cz_url(r"^test-email/$", views.TestEmailView),
    cz_url(r"^success/$", views.SuccessView),
    cz_url(r"^user-details/.json/$", views.UserDetailsView),
    cz_url(r"^tmp-space-view/$", views.TmpSpaceView),
    cz_url(r"^test-internet-access/$", views.TestInternetAccessView),
    cz_url(r"^pusher-authentication/$", views.PusherAuthenticationView),
    cz_url(r"^pusher-test/$", views.PusherTestView),
    cz_url(r"^ip-addresses/$", views.IpAddressView),
    cz_url(r"sample-pdf-spec/$", views.SamplePdfSpec),
    cz_url(r"sample-xlsx-view/$", views.SampleXlsxView),
]
