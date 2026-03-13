"""
Clone scheduled task and schedule it at some time in the future.
"""

import click

if __name__ == "__main__":
    import django

    django.setup()


from gstnapi.models import ScheduledTask


@click.command()
@click.option("--task-uuid", required=True, type=click.UUID, help="The UUID of the ScheduledTask")
@click.option(
    "--delay",
    required=True,
    type=int,
    help="The delay after which this task should be run",
)
def run(task_uuid, delay):
    task = ScheduledTask.objects2.get(uuid=task_uuid)
    newtask = task.clone(delay=delay)
    print(newtask)


if __name__ == "__main__":
    run()
