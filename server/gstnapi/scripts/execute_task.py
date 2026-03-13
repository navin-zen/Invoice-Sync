"""
Execute a ScheduledTask
"""

import sys

import click

from cz_utils.exceptions import DryRunSuccessException

if __name__ == "__main__":
    import django

    django.setup()

from django.db import transaction

from gstnapi.models import ScheduledTask


@click.command()
@click.option("--task-uuid", required=True, type=click.UUID, help="The UUID of the ScheduledTask")
@click.option("--real-run", is_flag=True, help="Whether this is a real run")
def run(task_uuid, real_run):
    task = ScheduledTask.objects2.get(uuid=task_uuid)
    if real_run:
        task.execute_once()
    else:
        try:
            with transaction.atomic():
                task.execute_once()
                raise DryRunSuccessException()
        except DryRunSuccessException:
            print("Dry Run was successful", file=sys.stderr)


if __name__ == "__main__":
    run()
