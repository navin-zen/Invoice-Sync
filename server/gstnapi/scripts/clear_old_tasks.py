"""
Clear old ScheduledTasks
"""

import click

if __name__ == "__main__":
    import django

    django.setup()

from django.db import connection

from gstnapi.models import ScheduledTask
from gstnapi.utils.task_utils import scheduled_task


@scheduled_task
def clear_old_tasks(min_age_days):
    if not min_age_days:
        min_age_days = 7
    ScheduledTask.objects2.can_be_cleared(min_age_days=min_age_days).delete()
    with connection.cursor() as cursor:
        cursor.execute("VACUUM VERBOSE ANALYZE gstnapi_scheduledtask")


@click.command()
@click.option(
    "--min-age-days",
    required=False,
    type=int,
    help="The minimum age of data above which to clear",
)
def run(min_age_days):
    clear_old_tasks(min_age_days)


if __name__ == "__main__":
    run()
