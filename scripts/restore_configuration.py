# Script to dump and load sql data.
# We backup and restore only the Configuration, GstIn, GlobalConfiguration and State models.

import os
import subprocess

import requests

if __name__ == "__main__":
    import django

    django.setup()


def main():
    subprocess.check_call(["./manage.py", "migrate"])
    token = os.environ.get("GSTZEN_AUTH_TOKEN", "")
    headers = {
        "Token": token,
    }
    response = requests.get(
        url="https://my.gstzen.in/~gstzen/a/restore-on-prem-configuration/",
        headers=headers,
        stream=True,
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("Could not restore data from GSTZen.")
        return
    subprocess.check_call(["./manage.py", "loaddata", "--format=json", "-"], stdin=response.raw)


if __name__ == "__main__":
    main()
