from django.utils.functional import cached_property as django_cached_property


class cached_property(django_cached_property):
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, "__doc__")
        self.name = name or func.__name__
