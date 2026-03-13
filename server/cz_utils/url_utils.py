import inflection
from django.contrib.admindocs.views import extract_views_from_urlpatterns
from django.db.transaction import non_atomic_requests
from django.http import QueryDict
from django.urls import get_resolver, re_path
from django.utils.safestring import mark_safe
from django.views.generic import View

from cz_utils.functools import lru_cache

__all__ = (
    "cz_url",
    "construct_cz_url",
    "CZ_HIDDEN_PREFIX",
    "CZ_INITIAL_PREFIX",
    "CZ_UUID",
    "CZ_SLUG",
    "CZ_SCHEMA",
    "view_class_for_urlname",
)

CZ_UUID = r"(?P<uuid>[-\w]+)"
CZ_UUID = r"(?P<uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
CZ_PK = r"(?P<pk>\d+)"
CZ_SLUG = r"(?P<slug>[-\w]+)"
# A uuid encoded using base64 encoding
CZ_UUID64 = r"(?P<uuid64>[-_A-Za-z0-9]{22})"
# The name of a multi-tenant schema, used for cz_helpdesk URLs
CZ_SCHEMA = r"~(?P<helpdesk_schema>[a-z]+)"
CZ_INITIAL_PREFIX = "cz:initial:"
CZ_HIDDEN_PREFIX = "cz:hidden:"


def construct_cz_url(url="", initial={}, hidden=[], otherargs=None):
    """
    Construct a URL with query parameters as per CloudZen convention.

    CloudZen follows the following convention for query parameters.
    Parameters prefixed with `cz:initial:` denote initial values for form
    fields. 'initial' is a dict specifying initial values.
    Parameters prefixed with `cz:hidden:` denote hidden fields in a form.
    'hidden' is a list specifying fields to be hidden.

    'otherargs' can be one of the following:
        1) a dict of other query args to be sent along with the url.
        2) a list/tuple of (key, value) tuples. This form supports multiple
        values for the same key.

    As per this convention, the URL is contructed as
        url?initial&hidden&otherargs
    """
    q = QueryDict(mutable=True)
    if otherargs:
        if isinstance(otherargs, (list, tuple)):
            for k, v in otherargs:
                q.appendlist(k, v)
        else:
            q.update(otherargs)
    q.update({f"{CZ_INITIAL_PREFIX}{k}": v for (k, v) in initial.items()})
    q.update({f"{CZ_HIDDEN_PREFIX}{k}": 1 for k in hidden})
    return "{}{}{}".format(url, "?" if url else "", mark_safe(q.urlencode()))


def cz_url(pattern, generic_view_class, atomic_requests=True):
    """
    Define a URL for a Django class-based generic view.

    As an example, if your class name is `CompanyList`, by defining
        cz_url(r'^companies/$', CompanyList)
    you will get a URL '/companies/' that invokes the view CompanyList. The
    name of the URL is autmatically constructed as 'company_list'. The
    fully qualified URL name is 'app_name:company_list' where app_name is
    the name of the app that defines the URL.
    """
    class_name = generic_view_class.__name__
    url_name = inflection.underscore(class_name)
    if inflection.camelize(url_name) != class_name:
        raise ValueError(f"View Class '{class_name}' is not uniquely underscore-able")
    view_func = generic_view_class.as_view()
    if not atomic_requests:
        view_func = non_atomic_requests(view_func)
    return re_path(pattern, view_func, name=url_name)


@lru_cache()
def view_funcs_mapping():
    """
    Returns a mapping of URL names to view functions
    """
    return {
        f"{apps[0]}:{name}": func
        for (func, _, apps, name) in extract_views_from_urlpatterns(get_resolver(None).url_patterns)
        if (apps and (len(apps) == 1))
    }


def view_class_from_func(func):
    """
    Get the View class from the func returned by View.as_func().
    """
    closure_cells = [c.cell_contents for c in (func.__closure__ or [])]
    closure = dict(zip(func.__code__.co_freevars, closure_cells))
    try:
        view_class = closure["cls"]
    except KeyError:
        return None
    if not issubclass(view_class, View):
        return None
    return view_class


def view_class_for_urlname(name):
    """
    The View class for a URL name.
    """
    func = view_funcs_mapping()[name]
    return view_class_from_func(func)
