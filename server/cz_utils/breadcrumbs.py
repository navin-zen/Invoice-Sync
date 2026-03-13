import abc
import inspect

from django.utils.functional import cached_property

import config.customizations.django.utils.inspect

from .templatetags.cloudzen_extras import verbose_name

__all__ = (
    "BreadCrumb",
    "RelatedObjectCreateBreadCrumb",
    "DetailBreadCrumb",
    "UpdateBreadCrumb",
    "DeleteBreadCrumb",
    "DetailFollowerBreadCrumb",
    "breadcrumb_factory",
    "breadcrumbify",
)


class BreadCrumb(metaclass=abc.ABCMeta):
    @cached_property
    def path(self):
        def walk(node):
            pathlength = 0
            while node is not None:
                if inspect.isclass(node) and issubclass(node, BreadCrumb):
                    node = node()
                elif isinstance(node, BreadCrumb):
                    pass
                else:
                    raise RuntimeError("Got an object that is not of type BreadCrumb")
                pathlength += 1
                if pathlength > 15:
                    raise RuntimeError("Maximum breadcrumb path length exceeded")
                if len(node.data) == 2:
                    (url, text) = node.data
                    long_text = ""
                elif len(node.data) == 3:
                    (url, text, long_text) = node.data
                else:
                    raise RuntimeError("Invalid breadcrumb specification")
                yield (url, text, long_text)
                node = node.prev

        return list(reversed(list(walk(self))))

    @abc.abstractproperty
    def data(self):
        raise NotImplementedError(f"{self.__class__.__name__}.data")

    @abc.abstractproperty
    def prev(self):
        """
        The previous link in the BreadCrumb chain.

        prev can be either an instance of BreadCrumb or a subclass of
        BreadCrumb.
        """
        raise NotImplementedError(f"{self.__class__.__name__}.prev")


class RelatedObjectCreateBreadCrumb(BreadCrumb):
    """
    BreadCrumb class for a CreateView that is related to a DetailView.
    """

    @abc.abstractproperty
    def create_model(self):
        """
        The model of the object to be created.
        """
        pass

    @abc.abstractproperty
    def related_detail_breadcrumb_class(self):
        """
        The BreadCrumb class of the DetailView under which we want to
        create this object.
        """
        pass

    def __init__(self, related_obj):
        self.related_obj = related_obj

    @cached_property
    def data(self):
        return ("", f"Create {verbose_name(self.create_model)}")

    @cached_property
    def prev(self):
        return self.related_detail_breadcrumb_class(self.related_obj)


class DetailBreadCrumb(BreadCrumb):
    """
    BreadCrumb class for a DetailView.
    """

    def __init__(self, obj):
        self.obj = obj

    @cached_property
    def data(self):
        return (self.obj.get_absolute_url(), str(self.obj))


class DetailFollowerBreadCrumb(BreadCrumb):
    """
    BreadCrumb class for a view that follows a DetailView.
    """

    @abc.abstractproperty
    def detail_breadcrumb_class(self):
        pass

    def __init__(self, obj):
        self.obj = obj

    @cached_property
    def prev(self):
        return self.detail_breadcrumb_class(self.obj)


class UpdateBreadCrumb(DetailFollowerBreadCrumb):
    """
    BreadCrumb class for an UpdateView.
    """

    @cached_property
    def data(self):
        return (self.obj.get_update_url(), "Update")


class DeleteBreadCrumb(DetailFollowerBreadCrumb):
    """
    BreadCrumb class for a DeleteView.
    """

    @cached_property
    def data(self):
        return (self.obj.get_delete_url(), "Delete")


def breadcrumb_factory(url, text, prev):
    class SomeBreadCrumb(BreadCrumb):
        @cached_property
        def data(self):
            return (url, text)

        @cached_property
        def prev(self):
            return prev

    return SomeBreadCrumb()


def breadcrumbify(module=None, argument=None, breadcrumb_class=None):
    """
    Define 'cz_breadcrumb' for a view class.

    This is a decorator that is invoked as follows:

        @breadcrumbify(breadcrumb_module, argument='foo')
        class MyView(View):
            pass

    This decorator makes the following assumptions/conventions.
        1) If breadcrumb_class is specified, we use that as the breadcrumb
           class. Otherwise, our breadcrumb class should be in
           breadcrumb_module.MyViewBC
        2) If the breadcrumb class __init__() needs one parameter/argument,
        we look in the following places:
            a) MyView.argument if argument is specified
            b) MyView.get_object()
        3) If the breadcrumb class __init__() needs more than one
            parameter, breadcrumbify's parameter `argument` must be a list or
            tuple of strings. The length of the list/tuple must be equal to
            the number of parameters that __init__ needs.

    Here's another example invocation where the breadcrumb class accepts
    two arguments:

        @breadcrumbify(breadcrumb_module, argument=['param1', 'param2'])
        class MyView(View):
            pass
    """

    def decorator(view):
        if (breadcrumb_class is None) and (module is None):
            raise ValueError("One of 'module' or 'breadcrumb_class' should be specified")
        if breadcrumb_class is None:
            view_name = view.__name__
            breadcrumb_name = f"{view_name}BC"
            breadcrumb_class_ = getattr(module, breadcrumb_name, None)
        else:
            breadcrumb_class_ = breadcrumb_class
        if not breadcrumb_class_:
            raise ValueError(f"Could not find breadcrumb class '{breadcrumb_name}'")
        if not inspect.isclass(breadcrumb_class_):
            raise TypeError(f"{breadcrumb_name} is not a class")
        # Breadcrumb class needs no argument
        if not inspect.isfunction(breadcrumb_class_.__init__):
            view.cz_breadcrumb = breadcrumb_class_
            return view
        # Use django.utils.inspect.getargspec instead of inspect.getargspec
        # https://github.com/django/django/pull/4846
        # https://groups.google.com/d/topic/django-developers/NZskysjasx8/discussion
        (args, varargs, keywords, defaults) = config.customizations.django.utils.inspect.getargspec(
            breadcrumb_class_.__init__
        )
        if any((i is not None) for i in [varargs, keywords, defaults]):
            raise ValueError(f"The signature of {breadcrumb_name}.__init__ is not simple.")
        if len(args) == 1:
            view.cz_breadcrumb = breadcrumb_class_
            return view
        elif len(args) == 2:
            if argument:

                @cached_property
                def cz_breadcrumb(self):
                    return breadcrumb_class_(getattr(self, argument))

                cz_breadcrumb.__set_name__(view, None)
                view.cz_breadcrumb = cz_breadcrumb
                return view
            elif inspect.isfunction(view.get_object):

                @cached_property
                def cz_breadcrumb(self):
                    return breadcrumb_class_(self.get_object())

                cz_breadcrumb.__set_name__(view, None)
                view.cz_breadcrumb = cz_breadcrumb
                return view
            else:
                raise NotImplementedError(f"Do not know how to construct '{breadcrumb_name}'")
        else:
            if not isinstance(argument, (list, tuple)):
                raise ValueError(f"While constructing {breadcrumb_name}, argument must be a list or tuple or strings")
            if len(argument) != (len(args) - 1):
                raise ValueError(f"While constructing {breadcrumb_name}, mismatch in number of arguments")

            @cached_property
            def cz_breadcrumb(self):
                return breadcrumb_class_(*[getattr(self, arg) for arg in argument])

            cz_breadcrumb.__set_name__(view, None)
            view.cz_breadcrumb = cz_breadcrumb
            return view

    return decorator
