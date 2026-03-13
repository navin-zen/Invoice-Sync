import datetime
import time
from datetime import timezone
from unittest import mock

from django.test import override_settings
from django.test.testcases import TestCase as DjangoTestCase
from pygstn.exceptions import EmptyResponseError
from pygstn.utils.environ import _setenv

from cz_utils.exceptions import SuspensionException, TooMuchForLambdaException
from cz_utils.fargate_utils import is_on_fargate
from cz_utils.testing_utils import check_instance_growth
from gstnapi.models import ScheduledTask, ScheduledTaskEnums
from gstnapi.utils.task_scheduler import choose_tasks
from gstnapi.utils.task_utils import scheduled_fargate_task, scheduled_task


@scheduled_task
def good_function():
    return 3


@scheduled_fargate_task
def long_function():
    time.sleep(1000000)
    return 3


@scheduled_task
def potential_long_function(is_long):
    """
    This function will initially be run on Lambda. If it raises
    TooMuchForLambdaException, it wil then be run on Fargate.
    """
    if not is_long:
        return "short"
    if not is_on_fargate():
        raise TooMuchForLambdaException()
    return "long"


@scheduled_task
def bad_function():
    raise ValueError("This is a bad function")


@scheduled_task
def not_enough_funds():
    raise SuspensionException("Not Enough Funds")


@scheduled_task
def transcient_failure():
    raise EmptyResponseError("Empty Response", {})


@override_settings(DEBUG=True)
class TestCase(DjangoTestCase):
    def test_tasks(self):
        self.assertEqual(good_function(), 3)
        with self.assertRaises(ValueError):
            bad_function()
        with self.assertRaises(SuspensionException):
            not_enough_funds()
        with self.assertRaises(EmptyResponseError):
            transcient_failure()
        min_time = datetime.datetime.min.replace(tzinfo=timezone.utc)
        with check_instance_growth(self, ScheduledTask, 4):
            good_function.at(min_time)()
            bad_function.at(min_time)()
            not_enough_funds.at(min_time)()
            transcient_failure.at(min_time)()
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 4)
        all_tasks = [_, bad_task, funds_task, trans_task] = ScheduledTask.objects2.to_be_run().order_by("create_date")
        for t in all_tasks:
            self.assertTrue((t.invocation_time is None) and (t.completion_time is None))
        self.assertFalse(bad_task.traceback_text)
        self.assertFalse(funds_task.traceback_text)
        self.assertFalse(trans_task.traceback_text)
        with mock.patch("gstnapi.models.rescheduled_datetime") as rsdtfn:
            rsdtfn.return_value = min_time
            # We run all functions
            ScheduledTask.process_tasks(is_async=False)
        # good_function ran, bad_function failed, not_enough_funds will not be re-run
        funds_task = ScheduledTask.objects2.get(uuid=funds_task.uuid)
        self.assertTrue((funds_task.invocation_time is not None) and (funds_task.completion_time is not None))
        self.assertTrue(funds_task.traceback_text)
        self.assertIn("funds", funds_task.traceback_text)
        # bad_function is eligible for retry, so is trans_task
        self.assertEqual(ScheduledTask.objects2.get(uuid=trans_task.uuid).status, ScheduledTask.S_FAILED_TRANSIENT)
        bad_task = ScheduledTask.objects2.get(uuid=bad_task.uuid)
        self.assertTrue((bad_task.invocation_time is not None) and (bad_task.completion_time is not None))
        self.assertTrue(bad_task.traceback_text)
        self.assertIn("This is a bad function", bad_task.traceback_text)
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 2)
        with mock.patch("gstnapi.models.rescheduled_datetime") as rsdtfn:
            rsdtfn.return_value = min_time
            ScheduledTask.process_tasks(is_async=False)  # bad_function and trans_task failed again
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 2)
        with mock.patch("gstnapi.models.rescheduled_datetime") as rsdtfn:
            rsdtfn.return_value = min_time
            ScheduledTask.process_tasks(is_async=False)  # bad_function failed again, but will not be re-run
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 0)
        # Test an invalid function
        st = ScheduledTask.new_task(
            tasktype=ScheduledTaskEnums.TT_LAMBDA,
            schema_name="unused",
            at=min_time,
            func_path="foo.bar.baz.nonexistent_function",
            args=[],
            kwargs={},
        )
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 1)
        self.assertEqual(ScheduledTask.objects2.get(uuid=st.uuid).status, ScheduledTask.S_INITIAL)
        ScheduledTask.process_tasks(is_async=False)
        self.assertEqual(ScheduledTask.objects2.get(uuid=st.uuid).status, ScheduledTask.S_INVALID_FUNC)
        self.assertEqual(ScheduledTask.objects2.to_be_run().count(), 0)

    def test_nodelay(self):
        with mock.patch("gstnapi.tasks.process_tasks") as process_tasks:
            self.assertFalse(process_tasks.called)
            with check_instance_growth(self, ScheduledTask, 1):
                good_function.delay(0)()
            with check_instance_growth(self, ScheduledTask, 1):
                good_function.nodelay()()
            # This will not be called in this test. Because we add it to transaction.on_commit
            # However, on production it will be called after the
            # transaction commits.
            self.assertFalse(process_tasks.called)

    def test_fargate_vs_lambda(self):
        with check_instance_growth(self, ScheduledTask, 2):
            good_function.delay(-1)()
            long_function.delay(-1)()
        (lambda_uuid, fargate_uuid) = reversed(ScheduledTask.objects2.order_by("-create_date").uuids()[:2])
        with mock.patch("gstnapi.tasks.execute_task") as execute_task:
            with mock.patch("gstnapi.tasks.execute_fargate_task") as execute_fargate_task:
                execute_task.assert_not_called()
                execute_fargate_task.assert_not_called()
                ScheduledTask.process_tasks()
        execute_task.assert_called_once_with(str(lambda_uuid))
        execute_fargate_task.assert_called_once_with(str(fargate_uuid))

    def test_too_much_for_lambda(self):
        # This function is too much for execution on Lambda
        with check_instance_growth(self, ScheduledTask, 2):
            potential_long_function.delay(-1)(is_long=False)
            potential_long_function.delay(-1)(is_long=True)
        (short_st, long_st) = reversed(ScheduledTask.objects2.order_by("-create_date")[:2])
        self.assertEqual(short_st.execute_once(), "short")
        with check_instance_growth(self, ScheduledTask, 1):
            self.assertEqual(long_st.execute_once(), None)
        long_fargate_st = ScheduledTask.objects2.order_by("create_date").last()
        with _setenv(LAMBDA_ON_FARGATE="1"):
            self.assertEqual(long_fargate_st.execute_once(), "long")

    def test_choose_tasks(self):
        # Test our task scheduler that chooses tasks for running
        self.assertEqual(choose_tasks(3, [], []), [])
        waiting_tasks = [("c1", "t1", 1), ("c2", "t2", 2)]
        self.assertEqual(choose_tasks(3, [], waiting_tasks), waiting_tasks)
        self.assertEqual(choose_tasks(0, [], waiting_tasks), [])
        self.assertEqual(choose_tasks(1, [], waiting_tasks), [("c1", "t1", 1)])
        self.assertEqual(choose_tasks(1, [("c1", "o1", -1)], waiting_tasks), [])
        self.assertEqual(choose_tasks(2, [("c1", "o1", -1)], waiting_tasks), [("c2", "t2", 2)])
        current_tasks = [
            ("c2", "o1", -1),
            ("c2", "o2", -2),
        ]
        waiting_tasks = [
            ("c2", "u1", 1),
            ("c2", "u2", 2),
            ("c2", "u3", 3),
            ("c1", "t1", 1),
            ("c1", "t2", 2),
            ("c1", "t3", 3),
        ]
        self.assertEqual(
            sorted(choose_tasks(6, current_tasks, waiting_tasks)),
            [
                ("c1", "t1", 1),
                ("c1", "t2", 2),
                ("c1", "t3", 3),
                ("c2", "u1", 1),
            ],
        )
        current_tasks = [("c3", "w1", 0)]
        waiting_tasks = [
            ("c1", "t1", 1),
            ("c1", "t2", 2),
            ("c1", "t3", 3),
            ("c1", "t4", 4),
            ("c1", "t5", 5),
            ("c2", "u1", 1),
            ("c2", "u2", 2),
            ("c2", "u3", 3),
            ("c2", "u4", 4),
            ("c2", "u5", 5),
            ("c3", "v1", 1),
            ("c3", "v2", 2),
        ]
        self.assertEqual(
            sorted(choose_tasks(6, current_tasks, waiting_tasks)),
            [
                ("c1", "t1", 1),
                ("c1", "t2", 2),
                ("c2", "u1", 1),
                ("c2", "u2", 2),
                ("c3", "v1", 1),
            ],
        )
        current_tasks = [("c3", "w1", 0)]
        waiting_tasks = [
            ("c1", "t1", 1),
            ("c1", "t2", 2),
            ("c1", "t3", 3),
            ("c1", "t4", 4),
            ("c1", "t5", 5),
        ]
        self.assertEqual(
            choose_tasks(4, current_tasks, waiting_tasks), [("c1", "t1", 1), ("c1", "t2", 2), ("c1", "t3", 3)]
        )
