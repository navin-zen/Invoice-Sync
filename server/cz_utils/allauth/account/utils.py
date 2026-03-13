def get_request_param(request, param, default=None):
    return request.POST.get(param) or request.GET.get(param, default)


def get_next_redirect_url(request, redirect_field_name="next"):
    """
    Returns the next URL to redirect to, if it was explicitly passed
    via the request.
    """
    redirect_to = get_request_param(request, redirect_field_name)
    return redirect_to
