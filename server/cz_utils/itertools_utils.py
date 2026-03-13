import collections
import itertools
from itertools import zip_longest


def flatten_dict(d, parent_key="", sep="."):
    """
    Flatten a nested dict.

    keys must all be strings. Joins keys using `sep`.
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d, sep="."):
    if not d:
        return {}
    assert all((k and isinstance(k, str)) for k in d.keys())
    data = sorted((tuple(k.split(sep)), v) for (k, v) in d.items())
    result = {}
    for key, group in itertools.groupby(data, key=lambda x: x[0][0]):
        group = list(group)
        (firstpath, firstvalue) = group[0]
        if (len(group) == 1) and (len(firstpath) == 1):
            result[key] = firstvalue
            continue
        if not all((len(k) > 1) for (k, _) in group):
            raise ValueError("Cannot unflatten this dictionary")
        result[key] = unflatten_dict({sep.join(k[1:]): v for (k, v) in group}, sep=sep)
    return result


def diff_objs(a, b):
    """
    Return differing portion between two objects.
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return (a, b)
    keys = set(a.keys()) | set(b.keys())
    new_a = {}
    new_b = {}
    for k in keys:
        if (k in a) and (k in b):  # Present in both
            (va, vb) = diff_objs(a[k], b[k])
            if va != vb:
                new_a[k] = va
                new_b[k] = vb
        elif k in a:  # Present in one
            new_a[k] = a[k]
        elif k in b:  # Present in the other
            new_b[k] = b[k]
    return (new_a, new_b)


def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in itertools.ifilterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


def align_iterables(inputs, missing=None, key=lambda x: x):
    """Align sorted iterables

    Yields tuples with values from the respective `inputs`, placing
    `missing` if the value does not exist in the corresponding
    iterable.

    Example: align_iterables([ 'bc', 'bf', '', 'abf' ]) yields:
        (None, None, None, 'a')
        ('b', 'b', None, 'b')
        ('c', None, None, None)
        (None, 'f', None, 'f')

    Adapted from: http://stackoverflow.com/a/18304897
    """
    End = object()

    def _is_smallest(smallest, x):
        return (x is not End) and (key(x) == smallest)

    iterators = [itertools.chain(i, [End]) for i in inputs]
    values = [next(i) for i in iterators]
    while not all(v is End for v in values):
        smallest = min(key(v) for v in values if v is not End)
        yield tuple((v if _is_smallest(smallest, v) else missing) for v in values)
        values = [(next(i) if _is_smallest(smallest, v) else v) for (i, v) in zip(iterators, values)]


def batch_list(lst, n=1):
    """
    Batch a list `lst` into batches of size `n`.

    Adapted from: https://stackoverflow.com/a/8290508
    """
    length = len(lst)
    for ndx in range(0, length, n):
        yield lst[ndx : min(ndx + n, length)]


def grouper(iterable, n, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks

    Copied from https://docs.python.org/2/library/itertools.html#recipes

    >>> list(grouper(range(7), 3, -1))
    [(0, 1, 2), (3, 4, 5), (6, -1, -1)]
    >>> list(grouper(range(7), 3))
    [(0, 1, 2), (3, 4, 5), (6, None, None)]
    """
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).

        for (i, has_more) in lookahead(lst):
            ...

    The variable has_more is False for the last iteration, True for the rest
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, True
        last = val
    # Report the last value.
    yield last, False


def pairwise(iterable):
    """
    s -> (s0,s1), (s1,s2), (s2, s3), ...

    >>> list(pairwise(''))
    []
    >>> list(pairwise('a'))
    []
    >>> list(pairwise([1, 2]))
    [(1, 2)]
    >>> list(pairwise(range(6)))
    [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def mergeiter(i1, i2, keyfn):
    """Returns the "merge" of i1 and i2.  i1 and i2 must be iteratable
    objects, and we assume that i1 and i2 are both individually sorted.

    This code is copied from
    http://code.activestate.com/recipes/197530-merging-two-sorted-iterators-into-a-single-iterato/

    After we upgrade to Python 3.5 calls to this function can be replaced
    with heapq.merge and this function can go away.
    """
    left, right = ExtendedIter(i1), ExtendedIter(i2)
    while 1:
        if not left.has_next():
            while 1:
                yield right.next()
        if not right.has_next():
            while 1:
                yield left.next()
        kl = keyfn(left.peek())
        kr = keyfn(right.peek())
        if kl <= kr:
            yield left.next()
        else:
            yield right.next()


class ExtendedIter:
    """An extended iterator that wraps around an existing iterators.
    It provides extra methods:

        has_next(): checks if we can still yield items.

        peek(): returns the next element of our iterator, but doesn't
                pass by it."""

    def __init__(self, i):
        self._myiter = iter(i)
        self._next_element = None
        self._has_next = 0
        self._prime()

    def has_next(self):
        """Returns true if we can call next() without raising a
        StopException."""
        return self._has_next

    def peek(self):
        """Nonexhaustively returns the next element in our iterator."""
        assert self.has_next()
        return self._next_element

    def next(self):
        """Returns the next element in our iterator."""
        if not self._has_next:
            raise StopIteration
        result = self._next_element
        self._prime()
        return result

    def _prime(self):
        """Private function to initialize the states of
        self._next_element and self._has_next.  We poke our
        self._myiter to see if it's still alive and kicking."""
        try:
            self._next_element = next(self._myiter)
            self._has_next = 1
        except StopIteration:
            self.next_element = None
            self._has_next = 0


def flatten1(it):
    """
    Flatten an iterable, 1-level deep
    >>> list(flatten1([[1, 2, 3], [4, 5], [6]]))
    [1, 2, 3, 4, 5, 6]
    """
    return itertools.chain.from_iterable(it)
