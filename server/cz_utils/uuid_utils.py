import uuid


def validate_uuid(s):
    """
    Check whether a string is a valid UUID.

    Returns True/False.
    """
    if s is None:
        return False
    if isinstance(s, uuid.UUID):
        return True
    try:
        return uuid.UUID(s)
    except (AttributeError, ValueError):
        return False


def validate_uuid_str(s):
    """
    Validate that we have an actual string object that is a UUID.
    """
    return isinstance(s, str) and validate_uuid(s)
