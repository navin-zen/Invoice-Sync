"""
Utility to create a new ScheduledTask
"""

import datetime

from django.db import transaction
from django.utils import timezone

from cz_utils.import_utils import get_func_task_path
from gstnapi.models import ScheduledTask, ScheduledTaskEnums


class scheduled_task:
    """
    Decorator that allows us to make a function one that can create a
    scheduled task.

        @scheduled_task
        def foo(args):
            pass

    Now, `foo` can be called as

        foo(1, 2, 3)  # Will be called immediately

    Or

        foo.delay(60)(1, 2, 3)  # Will be scheduled to run after 60 seconds

    Or

        foo.delay(0)(1, 2, 3)
        # Will be schedule to run immediately.  However, it will not
        # actually run immediately. The scheduler on AWS fires once every
        # minute.

    Or

        foo.nodelay()(1, 2, 3)
        # Will be scheduled and will be invoked immediately

    """

    TASK_TYPE = ScheduledTaskEnums.TT_LAMBDA

    def __init__(self, func=None):
        if func:
            self.func = func
            self.func_path = get_func_task_path(self.func)
            self.__doc__ = getattr(func, "__doc__")
        else:
            self.__doc__ = self.func = self.func_path = None
        self.scheduled_time = None
        self.run_immediately = False

    def _make_clone(self):
        clone = (self.__class__)()
        clone.func = self.func
        clone.func_path = self.func_path
        clone.__doc__ = self.__doc__
        return clone

    def __call__(self, *args, **kwargs):
        if not self.scheduled_time:
            return self.func(*args, **kwargs)
        schema_name = "unused"  # This will not be used
        ScheduledTask.new_task(
            self.TASK_TYPE, schema_name or "public", self.scheduled_time, self.func_path, args, kwargs
        )
        if self.run_immediately:
            from gstnapi.tasks import process_tasks

            transaction.on_commit(process_tasks)

    def at(self, time):
        clone = self._make_clone()
        clone.scheduled_time = time
        clone.run_immediately = False
        return clone

    def delay(self, seconds):
        clone = self._make_clone()
        clone.scheduled_time = timezone.now() + datetime.timedelta(seconds=seconds)
        clone.run_immediately = False
        return clone

    def nodelay(self):
        """
        Schedule it 5 seconds on the past and immediately process all tasks
        """
        clone = self.delay(-5)
        clone.run_immediately = True
        return clone


class scheduled_fargate_task(scheduled_task):
    TASK_TYPE = ScheduledTaskEnums.TT_FARGATE
