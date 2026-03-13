# pylint: disable=unused-wildcard-import,wildcard-import
"""
Test settings
"""

from .base import *  # NOQA
from .base import INSTALLED_APPS

IS_TESTING = True
DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
INSTALLED_APPS += ("django_nose",)


# Use nose to run all tests
TEST_RUNNER = "django_nose.NoseTestSuiteRunner"
NOSE_ARGS = []

INTERNAL_IPS = (
    "127.0.0.1",
    "10.0.2.2",
)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


# Copied from https://gist.github.com/NotSqrt/5f3c76cd15e40ef62d09
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
