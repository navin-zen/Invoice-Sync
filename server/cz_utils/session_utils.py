"""
Utility to write to the session
"""


class SessionUtil:
    DEFAULT = object()

    @classmethod
    def get(cls, session, path, default=DEFAULT):
        """
        Get data at a path within the session

        Raises KeyError if the path does not exist
        """
        assert isinstance(path, list) and len(path)
        value = session
        try:
            for p in path:
                value = value[p]
        except KeyError:
            if default is cls.DEFAULT:
                raise
            else:
                return default
        return value

    @classmethod
    def set(cls, session, path, value):
        """
        Set data at a path within the session

        In order to update the session, we must explicitly call
        session.__setitem__. We cannot simply write to a deeply nested
        value and leave it at that. The session will not know about it
        unless there is an explicit call.

        `dictionary` will be the value that we will write to session[path[0]]

        `d` is the temporary variable as we navigate down `dictionary`.
        """
        assert isinstance(path, list) and len(path)
        if len(path) == 1:
            session[path[0]] = value
            return
        try:
            dictionary = session[path[0]]
        except KeyError:
            dictionary = {}
        d = dictionary
        for p in path[1:-1]:
            try:
                d = d[p]
            except KeyError:
                d[p] = {}
                d = d[p]
        d[path[-1]] = value
        session[path[0]] = dictionary
