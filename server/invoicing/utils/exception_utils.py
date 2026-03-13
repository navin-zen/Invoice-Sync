import contextlib
import traceback


def exception_str(e):
    return str(e)


class ErrorWithInvoiceDetails(Exception):
    """
    Wrap an error with details of the invoice that we are processing, if any.
    """

    def __init__(self, exc, invoice=None, field=None):
        self.exc = exc
        self.invoice = invoice
        self.field = field

    def __str__(self):
        if self.invoice and self.field:
            return ("While processing the invoice number '{}', the '{}' field , has the following error: '{}'.").format(
                self.invoice, self.field, exception_str(self.exc)
            )
        elif self.invoice and not self.field:
            return "While processing the invoice number '{}', encountered the following error: '{}'.".format(
                self.invoice, exception_str(self.exc)
            )
        elif (not self.invoice) and self.field:
            return "While processing the '{}' field , encountered the following error: '{}'.".format(
                self.field, exception_str(self.exc)
            )
        else:
            return exception_str(self.exc)


class QuietValueError(ValueError):
    """
    A ValueError that we want to report in the UI but NOT print a traceback for
    in the console (because it's an 'expected' business logic error).
    """

    pass


class ErrorCollection(Exception):
    def __init__(self, arg):
        if isinstance(arg, str):
            self.errors = [arg]
        elif isinstance(arg, (list, tuple)):
            self.errors = arg
        else:
            raise TypeError(f"Unexpected type '{type(arg)}' while constructing ErrorCollection")


class ErrorGrouper:
    """
    A context manager to group errors, and keep doing work even in the face
    of Exceptions. It collects exceptions and raises a single one at the
    end.

    Here's how to use it:

    with ErrorGrouper() as eg:
        for i in range(10):
            with eg.wrapper():
                do_stuff()

    This code will execute all 10 iterations, even if one of the iterations
    throws an exception. The eg.wrapper() context does not allow exceptions
    to be raised. Instead, it saves them in the eg object. Whenver you see
    a with ErrorGrouper() as eg: you can think of it as raising all
    exceptions encountered underneath.

    with ErrorGrouper() as eg:
        with eg.wrapper():
            do_this()
        with eg.wrapper():
            do_that()

    This means, do_that() will execute when if do_this() raises an
    exception.

    with ErrorGrouper() as eg:
        with eg.wrapper():
            do_this()
            with eg.wrapper():
                do_that()
            do_something_else()
        or_something_else()

    The above program will always execute or_something_else(). It will
    execute do_something_else() if it reaches the do_that() line.
    """

    def __init__(self, raise_errors=True):
        self.errors = []
        self.raise_errors = raise_errors

    def __enter__(self):
        return self

    @contextlib.contextmanager
    def wrapper(self):
        self.current_errors = []  # Whether this wrapped execution got errors
        try:
            yield
        except ErrorCollection as ec:
            self.errors.extend(ec.errors)
            self.current_errors.extend(ec.errors)
        except QuietValueError as qv:
            # Report in UI but skip traceback in console
            self.errors.append(exception_str(qv))
            self.current_errors.append(exception_str(qv))
        except Exception as ex:
            traceback.print_exc()
            self.errors.append(exception_str(ex))
            self.current_errors.append(exception_str(ex))

    def __exit__(self, exc_type, exc_val, exc_traceback):
        if exc_type is None:  # We come here at the end
            if self.errors and self.raise_errors:
                traceback.print_exc()
                raise ErrorCollection(self.errors)
            else:
                return True
        else:
            # Ideally, we should never come here. All code within
            # ErrorGrouper should be called wrapped. However, just in case
            # we forget, we can raise the exception here
            return False


