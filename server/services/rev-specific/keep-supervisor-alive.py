#!/usr/bin/env python

"""
Wrapper script to keep supervisord alive.
"""

import os
import subprocess

import click

if os.environ.get("DJANGO_SETTINGS_MODULE", None) is None:
    raise ValueError("""
        Please set the DJANGO_SETTINGS_MODULE environment variable.
        Is the environment set before calling services/keep-supervisor-alive.py ?
    """)


CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervisord.conf")


def is_supervisord_running():
    try:
        output = subprocess.check_output(["supervisorctl", "-c", CONF, "pid"])
    except subprocess.CalledProcessError:
        return False
    int(output)
    return True


def run_supervisord():
    subprocess.check_call(["supervisord", "-c", CONF])


@click.command()
def check_and_run_supervisord():
    if is_supervisord_running():
        return
    run_supervisord()


if __name__ == "__main__":
    check_and_run_supervisord()
