# Script to dump and load sql data.
# We backup and restore only the Configuration, GstIn, GlobalConfiguration and State models.

import os
import subprocess
import sys

import requests

if __name__ == "__main__":
    import django

    django.setup()

from django.utils import timezone


def main():
    print(timezone.now().isoformat(), "Triggering auto backup to GSTZen", file=sys.stderr, flush=True)
    token = os.environ.get("GSTZEN_AUTH_TOKEN", "")
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MANAGE_PY = os.path.join(ROOT_DIR, "manage.py")
    if True:
        dump_data_output = subprocess.check_output(
            [
                MANAGE_PY,
                "dumpdata",
                "--format",
                "json",
                "einvoicing.Configuration",
                "einvoicing.PermanentAccountNumber",
                "einvoicing.GstIn",
                "einvoicing.GlobalConfiguration",
                "taxmaster.State",
            ]
        )
        if True:
            headers = {
                "Token": token,
            }
            r = requests.post(
                url="https://my.gstzen.in/~gstzen/a/backup-on-prem-configuration/", # TODO: We need to create new table for purchase sync on the GSTZen cloud server, since the endpoint is for einvoicing.
                data=dump_data_output,
                headers=headers,
            )
            print(f"Status: {r.status_code}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
