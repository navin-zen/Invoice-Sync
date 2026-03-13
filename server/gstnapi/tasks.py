import logging

# from cz_utils.async import cz_async_task, cz_fargate_task
from cz_utils.decorators import print_method_args

logger = logging.getLogger(__name__)


# @cz_async_task
def process_tasks():
    """
    Execute all tasks that can be run.
    """
    process_tasks_periodic_on_aws()


def process_tasks_periodic_on_aws():
    """
    Same as `process_tasks()` function above, but will be invoked
    periodically by Zappa on AWS.

    https://github.com/Miserlou/Zappa#scheduling
    """
    from gstnapi.models import ScheduledTask  # Importing here because this file is imported in models.py

    ScheduledTask.process_tasks()


def execute_task_internal(task_uuid):
    """
    Execute a single task.

    This function is invoked by process_tasks() above.
    """
    from gstnapi.models import ScheduledTask  # Importing here because this file is imported in models.py

    task = ScheduledTask.objects2.get(uuid=task_uuid)
    logger.info(f"Firing task {task_uuid} '{task}' for the {task.num_tries}th run")
    task.execute_once()
    # task has finished executing. We can find and execute other pending
    # tasks right away, instead of waiting for the AWS scheduler to fire
    # once every minute.
    process_tasks()


# @cz_async_task
@print_method_args
def execute_task(task_uuid):
    return execute_task_internal(task_uuid)


# @cz_fargate_task
@print_method_args
def execute_fargate_task(task_uuid):
    return execute_task_internal(task_uuid)
