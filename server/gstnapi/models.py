"""
Models related to our interaction with the GSTN API
"""

import datetime
import logging
import traceback

from django.conf import settings
from django.core.mail import mail_admins
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from jsonfield import JSONField
from pygstn.exceptions import EmptyResponseError, FileGoneError, Http503Error
from requests.exceptions import HTTPError

from cz_utils.django.db.fields import CzTextField, TrimmedCharField
from cz_utils.django.db.models import CloudZenModel
from cz_utils.exceptions import (
    GstnSessionRequiredException,
    GSTZenSoftwareErrorException,
    RateLimitException,
    SuspensionException,
    TooMuchForLambdaException,
)
from cz_utils.fargate_utils import is_on_fargate
from cz_utils.import_utils import import_and_get_task
from cz_utils.queryset_utils import CloudZenQuerySet
from cz_utils.text_utils import squeeze_space
from cz_utils.utils import is_valid_choice
from gstnapi.utils.task_scheduler import choose_tasks

logger = logging.getLogger(__name__)


def rescheduled_datetime(timedelta):
    """
    Return now + timedelta.

    This is a separate function so that we can mock it in tests
    """
    return timezone.now() + timedelta


class TransactionLog(CloudZenModel):
    """
    Log of a Transaction API call made to GSTN

    After careful throught, we are not linking to the Customer object
    directly. Instead, we are only specifying the schema_name.
    """

    created_by = None
    modified_by = None
    schema_name = TrimmedCharField(
        db_index=True,
        help_text=squeeze_space(
            """The name of
        the tenant/customer's schema."""
        ),
    )
    transaction_identifier = TrimmedCharField(
        db_index=True,
        help_text=squeeze_space(
            """The unique transaction identifier.
        https://groups.google.com/forum/#!msg/gst-suvidha-provider-gsp-discussion-group/6K0edbW6ooI/iI1cpR4-AAAJ
        """
        ),
    )
    url = models.URLField(
        max_length=1024,
        help_text=squeeze_space(
            """The
        URL Path of the request."""
        ),
    )
    headers = JSONField(
        default=dict,
        blank=True,
        help_text=squeeze_space(
            """The HTTP
        headers."""
        ),
    )
    payload = JSONField(
        default=dict,
        blank=True,
        help_text=squeeze_space(
            """The
        unencrypted JSON data sent in the payload."""
        ),
    )
    status_code = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The HTTP Status
        code of the response."""
        ),
    )
    elapsed = models.DurationField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The time time
        it took to get the response.
        http://docs.python-requests.org/en/latest/api/#requests.Response.elapsed"""
        ),
    )
    response = JSONField(
        default=dict,
        blank=True,
        help_text="The decrypted response data from received from GSTN.",
    )
    raw_response = models.BinaryField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The response
        content received from GSTN. Used only in the case of error
        responses when we are not able to set the `response` field."""
        ),
    )
    objects = models.Manager()
    objects2 = CloudZenQuerySet.as_manager()

    class Meta:
        default_permissions = ()

    def __str__(self):
        return f"Transaction {self.transaction_identifier}"


class ScheduledTaskEnums:
    (TT_LAMBDA, TT_FARGATE) = range(878, 878 + 2)

    TASK_TYPE_CHOICES = (
        (TT_LAMBDA, "Lambda"),
        (TT_FARGATE, "Fargate"),
    )


class ScheduledTaskQuerySet(CloudZenQuerySet):
    IS_FARGATE_TASK_QOBJ = Q(tasktype=ScheduledTaskEnums.TT_FARGATE)
    IS_LAMBDA_TASK_QOBJ = Q(tasktype=ScheduledTaskEnums.TT_LAMBDA) | Q(tasktype__isnull=True)

    def is_fargate(self):
        return self.filter(self.IS_FARGATE_TASK_QOBJ)

    def is_lambda(self):
        return self.filter(self.IS_LAMBDA_TASK_QOBJ)

    def to_be_run(self):
        """
        Filter which tasks are to be run.
        """
        return self.filter(
            Q(num_tries__lt=3),
            Q(status__in=ScheduledTask.TO_BE_RUN),
            (
                Q(rescheduled_time__isnull=True, scheduled_time__lte=timezone.now())
                | Q(
                    rescheduled_time__isnull=False,
                    rescheduled_time__lte=timezone.now(),
                )
            ),
        )

    def to_be_timed_out(self):
        """
        Tasks that should be marked as timed-out.
        """
        return self.currently_running().filter(
            (Q(self.IS_LAMBDA_TASK_QOBJ) & Q(invocation_time__lte=(timezone.now() - ScheduledTask.MAX_TIMEOUT)))
            | (
                Q(self.IS_FARGATE_TASK_QOBJ)
                & Q(invocation_time__lte=(timezone.now() - ScheduledTask.MAX_FARGATE_TIMEOUT))
            )
        )

    def currently_running(self):
        """
        Tasks that are currently running
        """
        return self.filter(status=ScheduledTask.S_RUNNING)

    def can_be_cleared(self, min_age_days=None):
        """
        Old tasks that can be cleared

        :param: min_age_days - The minimum age of the task (in days) that we can clear
        """
        if not min_age_days:
            min_age_days = 7
        min_age_days = max(min_age_days, 7)  # Just in case min_age_days happens to be negative
        return self.filter(
            status__in=[
                ScheduledTask.S_COMPLETE,
                ScheduledTask.S_INVALID_FUNC,
                ScheduledTask.S_WONT_RETRY,
                ScheduledTask.S_FAILED_TRANSIENT,
                ScheduledTask.S_TOO_MUCH_FOR_LAMBDA,
            ]
        ).filter(create_date__lte=timezone.now() - datetime.timedelta(days=min_age_days))


class ScheduledTask(CloudZenModel):
    """
    Event Queue of API calls that we want to execute at a later time.

    After careful throught, we are not linking to the Customer object
    directly. Instead, we are only specifying the schema_name.

    The actuals details of the task such as the name of the task and the
    arguments will be in 'metadata'.

    ScheduledTask.process_tasks() should be invoked periodically, say once
    every 2 minutes.

    Create a new task using ScheduledTask.new_task() or using the
    @scheduled_task decorator in gstnapi.utils.task_utils
    """

    MAX_TIMEOUT = datetime.timedelta(seconds=810)  # ~13 minutes
    MAX_FARGATE_TIMEOUT = datetime.timedelta(seconds=(60 * 60 * 12))  # 12 hours

    created_by = None
    modified_by = None

    (
        S_INITIAL,
        S_RUNNING,
        S_COMPLETE,
        S_TIMED_OUT,
        S_FAILED,
        S_INVALID_FUNC,
        S_WONT_RETRY,
        S_FAILED_TRANSIENT,
        S_TOO_MUCH_FOR_LAMBDA,
        S_FAILED_SOFTWARE_ERROR,
        S_FAILED_TIMING_ERROR,
    ) = range(11000, 11011)

    # Tasks in these states should be tried again
    TO_BE_RUN = [
        S_INITIAL,
        S_TIMED_OUT,
        S_FAILED,
        S_FAILED_TRANSIENT,
    ]

    STATUS_CHOICES = (
        (S_INITIAL, "Initial"),
        (S_RUNNING, "Running"),
        (S_COMPLETE, "Completed Successfully"),
        (S_TIMED_OUT, "Task has timed-out"),
        (S_FAILED, "Failed"),
        (S_INVALID_FUNC, "Requested task is not a valid function"),
        (S_WONT_RETRY, "Won't retry after this Failure"),
        (S_FAILED_TRANSIENT, "Transient failure (not in our control)"),
        (S_TOO_MUCH_FOR_LAMBDA, "Too much for Lambda"),
        (S_FAILED_SOFTWARE_ERROR, "Failed (because of software bug)"),
        (
            S_FAILED_TIMING_ERROR,
            "Failed because of some timing error",
        ),  # Transcient failure, retry won't help
    )

    NON_RETRYABLE_EXCEPTIONS = (
        SuspensionException,
        GstnSessionRequiredException,
        RateLimitException,
        Http503Error,
    )
    """
    If we get any of these exceptions, we won't re-run the task
    """

    TRANSCIENT_FAILURE_EXCEPTIONS = (EmptyResponseError, HTTPError)
    """
    These are transcient failures. We should retry, but these errors are
    not in our control.
    """

    TIMING_FAILURE_EXCEPTIONS = (FileGoneError,)
    """
    If we get these exceptions, we won't re-run the task, but it indicates
    an error on our side not on that of the user. That is we don't care
    that much about NON_RETRYABLE_EXCEPTIONS shown above. But, we do care
    about TIMING_FAILURE_EXCEPTIONS. We want to monitor them and see that we
    don't have a lot of those.
    """

    schema_name = TrimmedCharField(
        db_index=True,
        help_text=squeeze_space(
            """The name of
        the tenant/customer's schema."""
        ),
    )
    scheduled_time = models.DateTimeField(
        help_text=squeeze_space(
            """The
        time at which this task is scheduled."""
        )
    )
    rescheduled_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The time at which
        this task is re-scheduled, in case of failure."""
        ),
    )
    invocation_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The time at which
        this task is executed. If a task is in the running state for a very
        long time, we can take measures to retry it."""
        ),
    )
    completion_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The time at which
        this task completed. Helps us know the duration of the Task."""
        ),
    )
    status = models.PositiveIntegerField(
        db_index=True,
        choices=STATUS_CHOICES,
        default=S_INITIAL,
        help_text="The status of this task.",
    )
    tasktype = models.PositiveIntegerField(
        choices=ScheduledTaskEnums.TASK_TYPE_CHOICES,
        null=True,
        help_text="The type of task. Used for scheduling on Lambda/Fargate",
    )
    num_tries = models.PositiveIntegerField(
        default=0,
        help_text=squeeze_space(
            """The number of times we have
        tried to excute this task."""
        ),
    )
    traceback_text = CzTextField(blank=True, help_text="""Any traceback, in case of exception""")
    remarks = CzTextField(blank=True)
    metadata = JSONField(default=dict, editable=False)
    objects = models.Manager()
    objects2 = ScheduledTaskQuerySet.as_manager()

    class Meta:
        default_permissions = ()

    @cached_property
    def execution_time(self):
        if self.invocation_time and self.completion_time and (self.invocation_time <= self.completion_time):
            return self.completion_time - self.invocation_time
        return None

    @classmethod
    def new_task(cls, tasktype, schema_name, at, func_path, args, kwargs):
        is_valid_choice(tasktype, ScheduledTaskEnums.TASK_TYPE_CHOICES)
        assert isinstance(schema_name, str)
        assert isinstance(at, datetime.datetime)
        assert isinstance(func_path, str)
        metadata = dict(fn=func_path, args=args, kwargs=kwargs)
        st = ScheduledTask(
            tasktype=tasktype,
            schema_name=schema_name,
            scheduled_time=at,
            metadata=metadata,
        )
        st.full_clean()
        st.save()
        logger.info(f"New Task: {st}")
        return st

    def clone(self, delay=0, otherattrs={}):
        """
        Clone an existing task and schedule it at time specified by `delay`.

        Clone `self` without modifying `self`.
        """
        task = ScheduledTask(
            schema_name=self.schema_name,
            scheduled_time=timezone.now() + datetime.timedelta(seconds=delay),
            status=ScheduledTask.S_INITIAL,
            tasktype=self.tasktype,
            num_tries=0,
            traceback_text="",
            remarks=self.remarks,
            metadata=self.metadata,
        )
        for k, v in otherattrs.items():
            setattr(task, k, v)
        task.full_clean()
        task.save()
        return task

    @classmethod
    def process_tasks(cls, is_async=True):
        """
        Choose the tasks for execution and start them.
        """
        cls.timeout_tasks()
        cls.start_tasks(is_async=is_async)

    @classmethod
    def timeout_tasks(cls):
        """
        Timeout old tasks
        """
        with transaction.atomic():
            queryset = ScheduledTask.objects2.to_be_timed_out()
            if not queryset.exists():
                return
            uuids = queryset.uuids().as_set()
            queryset.update(status=cls.S_TIMED_OUT)
        for task in ScheduledTask.objects2.filter(uuid__in=uuids):
            logger.warning(f"Timing out task: {task}")

    @classmethod
    def start_tasks(cls, is_async=True, max_slots=None):
        """
        Fire up the 'ready' tasks.

        :param: is_async - Whether to execute the tasks asynchronously
        :param: max_slots - The maximum number of task slots that we have

        The default is to execute asynchronously. Only for testing purposes
        we execute synchronously.
        """
        if True:  # Just to keep the diff small
            waiting_qs = ScheduledTask.objects2.to_be_run()
            if not waiting_qs.exists():
                return
            current_tasks = (
                ScheduledTask.objects2.currently_running()
                .values_list(
                    "schema_name",
                    "uuid",
                    "scheduled_time",
                )
                .as_list()
            )
            waiting_tasks = waiting_qs.values_list("schema_name", "uuid", "scheduled_time").as_list()
            max_slots = max_slots or settings.CZ_MAX_NUM_SCHEDULED_TASKS
            chosen_ones = choose_tasks(max_slots, current_tasks, waiting_tasks)
            chosen_uuids = [uuid for (_, uuid, _) in chosen_ones]
        fargate_uuids = ScheduledTask.objects2.filter(uuid__in=chosen_uuids).is_fargate().uuids().as_set()
        lambda_uuids = ScheduledTask.objects2.filter(uuid__in=chosen_uuids).is_lambda().uuids().as_set()
        from gstnapi.tasks import execute_fargate_task, execute_task

        for u in chosen_uuids:
            locked_qs = waiting_qs.select_for_update().filter(uuid=u)
            with transaction.atomic():
                # This is the critical section, where we do a
                # select_for_update() and set the status to S_RUNNING.
                # Even when there are multiple instances of this function
                # running in parallel, there can be only one "winner" that
                # sets status to running.
                t = locked_qs.value("status").first()
                if not t:
                    continue
                if t not in cls.TO_BE_RUN:
                    continue
                locked_qs.update(
                    status=cls.S_RUNNING,
                    invocation_time=timezone.now(),
                    num_tries=F("num_tries") + 1,
                )
            if is_async:
                if u in fargate_uuids:
                    execute_fargate_task(force_str(u))
                elif u in lambda_uuids:
                    execute_task(force_str(u))
            else:
                ScheduledTask.objects2.get(uuid=u).execute_once()

    def execute_once(self):
        """
        Tries to execute the task once (synchronously)

        The task function also should be synchronous. It should not be a
        function that executes asynchronously (i.e., in Celery or AWS SNS)
        """
        result = self.execute_once_internal()
        self.completion_time = timezone.now()
        self.save(
            update_fields=[
                "status",
                "traceback_text",
                "completion_time",
                "rescheduled_time",
            ]
        )
        return result

    def execute_once_internal(self):
        fn = self.get_function()
        if not fn:
            self.status = self.S_INVALID_FUNC
            return
        args = self.metadata["args"]
        kwargs = self.metadata["kwargs"]
        try:
            result = fn(*args, **kwargs)
        except self.TIMING_FAILURE_EXCEPTIONS:  # Won't retry
            self.status = self.S_FAILED_TIMING_ERROR
            self.add_traceback()
            return
        except GSTZenSoftwareErrorException:  # Won't retry
            # This is a software/logic error. Unless we fix our code, this
            # error will not go away. There is no point re-trying this
            # task
            subject = f"Scheduled Task Failure - {self.uuid}"
            mail_admins(subject, f"Please investigate - {self.uuid}", fail_silently=True)
            self.status = self.S_FAILED_SOFTWARE_ERROR
            self.add_traceback()
            return
        except TooMuchForLambdaException:
            # This task cannot run within Lambda's time/memory limits
            # Create a clone that should be run on Fargate
            self.status = self.S_TOO_MUCH_FOR_LAMBDA
            self.add_traceback()
            if not is_on_fargate():
                # Precaution. Don't want an infinite recursion of Fargate
                # Tasks raising TooMuchForLambdaException
                self.clone(otherattrs={"tasktype": ScheduledTaskEnums.TT_FARGATE})
            return
        except self.NON_RETRYABLE_EXCEPTIONS:  # Won't retry
            self.status = self.S_WONT_RETRY
            self.add_traceback()
            return
        except self.TRANSCIENT_FAILURE_EXCEPTIONS:  # Will retry
            self.rescheduled_time = rescheduled_datetime(datetime.timedelta(seconds=90))
            self.status = self.S_FAILED_TRANSIENT
            self.add_traceback()
            return
        except Exception:  # Will retry
            self.status = self.S_FAILED
            self.rescheduled_time = rescheduled_datetime(datetime.timedelta(seconds=90))
            self.add_traceback()
            logger.exception("ScheduledTask execution failure")
            return
        self.status = self.S_COMPLETE
        return result

    @cached_property
    def function_name(self):
        return self.metadata["fn"]

    @cached_property
    def function_basename(self):
        return self.function_name.split(".")[-1]

    def get_function(self):
        function_name = self.function_name
        try:
            return import_and_get_task(function_name)
        except (ImportError, AttributeError):
            return None

    def add_traceback(self):
        """
        Add the traceback (within an exception) to traceback_text
        """
        self.traceback_text = "{}\n\n{}\n\n{}".format(
            (self.traceback_text or ""),
            "-" * 72,
            traceback.format_exc(),
        )

    def __str__(self):
        return f"Task `{self.function_name}` scheduled @ {self.scheduled_time}"
