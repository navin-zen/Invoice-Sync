import contextlib
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext


@contextlib.contextmanager
def patch_file_field(model, fieldname, filename="hello-world.txt"):
    """
    Patch/Mock the storage of a CzFileField of a model.

    `filename` is the name to set to the file.

    This is so that accesses to the field do not touch the filesystem (or
    in our case AWS S3).
    """
    field = model._meta.get_field(fieldname)
    with mock.patch.object(field, "storage") as storage:
        storage.save.return_value = filename
        storage.url.return_value = "https://s3.amazonaws.example.com/" + filename
        yield storage


@contextlib.contextmanager
def check_instance_growth(testcase, model, delta):
    """
    Check that we have created `delta` instances with this context.

    Here's are examples of using this context manager

        with check_instance_growth(testcase, Customer, 1):
            # Code that creates a new Customer

        with check_instance_growth(testcase, Document, -1):
            # Code that deletes a Document
    """
    num_instances_before = model._default_manager.count()
    yield
    num_instances_after = model._default_manager.count()
    testcase.assertEqual(num_instances_before + delta, num_instances_after)


class _AssertMaxQueriesContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self)
        self.test_case.assertLessEqual(
            executed,
            self.num,
            "%d queries executed, at most %d expected\nCaptured queries were:\n%s"
            % (executed, self.num, "\n".join(query["sql"] for query in self.captured_queries)),
        )


def check_max_queries(testcase, num, *args, **kwargs):
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    conn = connections[using]
    return _AssertMaxQueriesContext(testcase, num, conn)


def contains_subset(a, b):
    """
    a is a superset of b

    where a and b are complex datastructures.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return all((k in a) and contains_subset(a[k], v) for (k, v) in b.items())
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return (len(a) == len(b)) and all(contains_subset(ai, bi) for (ai, bi) in zip(a, b))
    return a == b
