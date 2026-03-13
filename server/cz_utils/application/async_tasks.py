from zappa.asynchronous import task_sns

from cz_utils.decorators import print_method_args

"""
Zappa asynchronous tasks
https://github.com/Miserlou/Zappa/#asynchronous-task-execution
"""


@task_sns
@print_method_args
def debug_task(*args, **kwargs):
    pass
