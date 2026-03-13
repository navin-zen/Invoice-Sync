from functools import lru_cache as functools_lru_cache

from django.conf import settings


def lru_cache(maxsize=128, typed=False):
    """
    We have to disable lru_cache during testing when we use lru_cache to
    return objects that disappear between tests.
    """
    if settings.IS_TESTING:

        def decorating_function(user_fuction):
            return user_fuction

        return decorating_function
    else:
        return functools_lru_cache(maxsize, typed)
