"""
Useful decorators by CloudZen.
"""

import functools
import logging
import time

from django.shortcuts import get_object_or_404

from config.customizations.django.utils.functional import cached_property

logger = logging.getLogger(__name__)


def print_method_args(func):
    """
    Decorator that prints out the arguments passed to a function before calling it

    Obtained from
    http://stackoverflow.com/questions/6200270/decorator-to-print-function-call-details-parameters-names-and-effective-values
    """
    code = func.__code__
    argnames = code.co_varnames[: code.co_argcount]
    fname = func.__name__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        all_args = (
            list(zip(argnames, args[: len(argnames)])) + [("args", list(args[len(argnames) :]))] + [("kwargs", kwargs)]
        )
        arg_details = ", ".join(("%s=%r" % entry) for entry in all_args)
        logger.info(f"Call to function: {fname}({arg_details})")
        return func(*args, **kwargs)

    return wrapper


def name_it(name):
    """
    A decorator that sets a class's __name__.
    """

    def decorator(cls):
        cls.__name__ = name
        return cls

    return decorator


def instance_from_url(model, property_name=None, query_field="pk", url_kwarg="pk"):
    """
    Add a property named 'property_name' to a view.

    The property returns an instance of 'model' as specified in the view's
    URL. If property_name is not specified, we use the lower-cased name of
    the model as the property's name.

    :param: model - The model to get the instance/object from
    :param: property_name - The name of the field (within the view) in
        which to provide the instance
    :param: query_field - The name of the field, within the model, we want
        to query get the instance/object
    :param: url_kwarg - The name of the URL parameter where we can get the
        value for looking up the model
    """
    if property_name is None:
        property_name = model.__name__.lower()

    def _get_instance(self):
        return get_object_or_404(model, **{query_field: self.kwargs.get(url_kwarg, "")})

    def decorator(view):
        cp = cached_property(_get_instance, name=property_name)
        cp.__set_name__(view, property_name)
        setattr(view, property_name, cp)
        return view

    return decorator


def instance_from_url_uuid(model, property_name=None, query_field="uuid", url_kwarg="uuid"):
    return instance_from_url(model, property_name=property_name, query_field=query_field, url_kwarg=url_kwarg)


def instance_from_get_object(property_name):
    """
    Add a property named 'property_name' to a view.

    The property returns the value of get_object().
    """

    def _get_instance(self):
        return self.get_object()

    def decorator(view):
        cp = cached_property(_get_instance, name=property_name)
        cp.__set_name__(view, property_name)
        setattr(view, property_name, cp)
        return view

    return decorator


def constructor(*args):
    """
    Class decorator to declare the __init__ of a class.

    The decorator defines the constructor function (i.e. __init__) of the
    class. The constructor accepts len(args) parameters and sets instance
    variables one for each arg specified in args. The following class

    class Point(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y

    can be written as

    @constructor('x', 'y')
    class Point(object):
        pass
    """
    if not all(isinstance(a, str) for a in args):
        raise ValueError("All arguments to constructor() must be strings.")

    def decorator(cls):
        if len(args) == 0:
            pass
        elif len(args) == 1:

            def fn(self, arg0):
                setattr(self, args[0], arg0)

            cls.__init__ = fn
        elif len(args) == 2:

            def fn(self, arg0, arg1):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)

            cls.__init__ = fn
        elif len(args) == 3:

            def fn(self, arg0, arg1, arg2):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)
                setattr(self, args[2], arg2)

            cls.__init__ = fn
        elif len(args) == 4:

            def fn(self, arg0, arg1, arg2, arg3):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)
                setattr(self, args[2], arg2)
                setattr(self, args[3], arg3)

            cls.__init__ = fn
        elif len(args) == 5:

            def fn(self, arg0, arg1, arg2, arg3, arg4):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)
                setattr(self, args[2], arg2)
                setattr(self, args[3], arg3)
                setattr(self, args[4], arg4)

            cls.__init__ = fn
        elif len(args) == 6:

            def fn(self, arg0, arg1, arg2, arg3, arg4, arg5):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)
                setattr(self, args[2], arg2)
                setattr(self, args[3], arg3)
                setattr(self, args[4], arg4)
                setattr(self, args[5], arg5)

            cls.__init__ = fn
        elif len(args) == 7:

            def fn(self, arg0, arg1, arg2, arg3, arg4, arg5, arg6):
                setattr(self, args[0], arg0)
                setattr(self, args[1], arg1)
                setattr(self, args[2], arg2)
                setattr(self, args[3], arg3)
                setattr(self, args[4], arg4)
                setattr(self, args[5], arg5)
                setattr(self, args[6], arg6)

            cls.__init__ = fn
        else:
            raise NotImplementedError("More than 7 arguments not supported at the moment.")
        return cls

    return decorator


def typed_constructor(*args):
    """
    Class decorator to declare the __init__ of a class.

    In addition to @constructor above, typechecks the constructor
    parameters

    class Point(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y

    can be written as

    @constructor(('x', float), ('y', float))
    class Point(object):
        pass
    """
    if not all((isinstance(a, tuple) and (len(a) == 2) and isinstance(a[0], str)) for a in args):
        raise ValueError("All arguments to typed_constructor() must be 2-tuples.")

    def decorator(cls):
        if len(args) == 0:
            pass
        elif len(args) == 1:

            def fn(self, arg0):
                setattr(self, args[0][0], arg0)
                assert isinstance(arg0, args[0][1])

            cls.__init__ = fn
        elif len(args) == 2:

            def fn(self, arg0, arg1):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])

            cls.__init__ = fn
        elif len(args) == 3:

            def fn(self, arg0, arg1, arg2):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                setattr(self, args[2][0], arg2)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])
                assert isinstance(arg2, args[2][1])

            cls.__init__ = fn
        elif len(args) == 4:

            def fn(self, arg0, arg1, arg2, arg3):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                setattr(self, args[2][0], arg2)
                setattr(self, args[3][0], arg3)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])
                assert isinstance(arg2, args[2][1])
                assert isinstance(arg3, args[3][1])

            cls.__init__ = fn
        elif len(args) == 5:

            def fn(self, arg0, arg1, arg2, arg3, arg4):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                setattr(self, args[2][0], arg2)
                setattr(self, args[3][0], arg3)
                setattr(self, args[4][0], arg4)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])
                assert isinstance(arg2, args[2][1])
                assert isinstance(arg3, args[3][1])
                assert isinstance(arg4, args[4][1])

            cls.__init__ = fn
        elif len(args) == 6:

            def fn(self, arg0, arg1, arg2, arg3, arg4, arg5):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                setattr(self, args[2][0], arg2)
                setattr(self, args[3][0], arg3)
                setattr(self, args[4][0], arg4)
                setattr(self, args[5][0], arg5)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])
                assert isinstance(arg2, args[2][1])
                assert isinstance(arg3, args[3][1])
                assert isinstance(arg4, args[4][1])
                assert isinstance(arg5, args[5][1])

            cls.__init__ = fn
        elif len(args) == 7:

            def fn(self, arg0, arg1, arg2, arg3, arg4, arg5, arg6):
                setattr(self, args[0][0], arg0)
                setattr(self, args[1][0], arg1)
                setattr(self, args[2][0], arg2)
                setattr(self, args[3][0], arg3)
                setattr(self, args[4][0], arg4)
                setattr(self, args[5][0], arg5)
                setattr(self, args[6][0], arg6)
                assert isinstance(arg0, args[0][1])
                assert isinstance(arg1, args[1][1])
                assert isinstance(arg2, args[2][1])
                assert isinstance(arg3, args[3][1])
                assert isinstance(arg4, args[4][1])
                assert isinstance(arg5, args[5][1])
                assert isinstance(arg6, args[6][1])

            cls.__init__ = fn
        else:
            raise NotImplementedError("More than 7 arguments not supported at the moment.")
        return cls

    return decorator


def ttl_cache(ttl=300):
    """
    A decorator for functions that we want to be called only once every
    `ttl` seconds.

    This is mainly for getting credentials from AWS when creating an AWS
    Client. AWS changes the credentials every few minutes. The AWS client
    will retrieve the credentials as per
    https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#instance-metadata-security-credentials

    We do not want to create the client every time. At the same time, when
    credentials expire, we want to get a new client. By using this
    decorator as shown below

        @ttl_cache(ttl=600)
        def get_client():
            return boto3.client("s3", ...)

    boto3.client() will be called only once every 10 minutes (600 seconds).
    """

    def decorator(f):
        @functools.lru_cache(maxsize=1)
        def inner_wrapper(timestamp, *args, **kwargs):
            return f(*args, **kwargs)

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            timestamp = int(time.time()) // int(ttl)
            return inner_wrapper(timestamp, *args, **kwargs)

        return wrapper

    return decorator


def as_list(f):
    """
    Decorator to convert iterator output to a list
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return list(f(*args, **kwargs))

    return wrapper


def log_execution_time(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        rv = f(*args, **kwargs)
        end = time.time()
        elapsed = end - start
        logger.debug("Elapsed time (seconds) of %s: %d", f.__name__, elapsed)
        return rv

    return wrapper
