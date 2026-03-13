import string
import uuid
from os.path import splitext

import django.utils.dateformat
import django.utils.timezone


def get_randomized_filename(filename, is_temporary=False):
    """
    Get a randomized filename based on filename.

    We only use the extension and nothing else in generating the randomized
    filename.
    """
    now = django.utils.timezone.now()
    timestamp = django.utils.dateformat.format(now, "YmdHis")
    _, extension = splitext(filename)
    extension = "".join(i for i in extension if i in ("." + string.digits + string.ascii_letters))
    return "{}/czfilefield/file-{}-{}{}".format(
        "temporary" if is_temporary else "gstzen",
        timestamp,
        uuid.uuid4().hex,
        extension.strip()[:6],
    )
