from itertools import izip_longest


_marker = object()
def chunked(iterable, n):
    """Break an iterable into tuples of a given length::

        >>> list(chunked([1, 2, 3, 4, 5, 6, 7], 3))
        [(1, 2, 3), (4, 5, 6), (8,)]

    If the length of ``iterable`` is not evenly divisible by ``n``, the last
    returned tuple will be shorter.

    This is useful for splitting up a computation on a large number of keys
    into batches, to be pickled and sent off to worker processes. One example
    is operations on rows in MySQL, which does not implement server-side
    cursors properly and would otherwise load the entire dataset into RAM on
    the client.

    """
    # Doesn't seem to run into any number-of-args limits.
    for group in izip_longest(*[iter(iterable)] * n, fillvalue=_marker):
        if group[-1] is _marker:
            # If this is the last group, shuck off the padding:
            group = tuple(x for x in group if x is not _marker)
        yield group


def first(iterable, default=_marker):
    """Return the first item of an iterable, ``default`` if there is none.

        >>> first([2, 3, 4])
        2
        >>> first([], 'some default')
        'some default'

    If ``default`` is not provided and there are no items in the iterable,
    raise ``ValueError``.

    ``first()`` is less verbose than ``next(iter(...))``, especially if you
    want to provide a fallback value.

    """
    try:
        return next(iter(iterable))
    except StopIteration:
        if default is _marker:
            raise ValueError('first() was called on an empty iterable, and no '
                             'default value was provided.')
        return default


class peekable(object):
    """Wrapper for an iterator to allow 1-item lookahead

    Call ``peek()`` on the result to get the value that will next pop out of
    ``next()``, without advancing the iterator:

        >>> p = peekable(xrange(2))
        >>> p.peek()
        0
        >>> p.next()
        0
        >>> p.peek()
        1
        >>> p.next()
        1

    ``peek()`` raises ``StopIteration`` if there are no items left.

    """
    # Lowercase to blend in with itertools. The fact that it's a class is an
    # implementation detail.

    def __init__(self, iterable):
        self._it = iter(iterable)

    def __iter__(self):
        return self

    def __nonzero__(self):
        try:
            self.peek()
        except StopIteration:
            return False
        return True

    def peek(self):
        """Return the item that will be next returned from ``next()``.

        Raise ``StopIteration`` if there are no items left.

        """
        # TODO: Give peek a default arg. Raise StopIteration only when it isn't
        # provided. If it is, return the arg. Just like get('key', object())
        if not hasattr(self, '_peek'):
            self._peek = self._it.next()
        return self._peek

    def next(self):
        ret = self.peek()
        del self._peek
        return ret


def collate(*iterables, **kwargs):
    """Return an iterable sorted merge of the already-sorted items from each of
    ``iterables``.

        >>> list(collate('ACDZ', 'AZ', 'JKL'))
        ['A', 'A', 'C', 'D', 'J', 'K', 'L', 'Z', 'Z']

    :arg key: A function that returns a comparison value for an item. Defaults
        to the identity function.
    :arg reverse: If ``reverse=True`` is passed, iterables must return their
        results in descending order rather than ascending.

    If the elements of the passed-in iterables are out of order, you might get
    unexpected results.

    """
    key = kwargs.pop('key', lambda a: a)
    reverse = kwargs.pop('reverse', False)

    min_or_max = max if reverse else min
    peekables = [peekable(it) for it in iterables]
    peekables = [p for p in peekables if p]  # Kill empties.
    while peekables:
        _, p = min_or_max((key(p.peek()), p) for p in peekables)
        yield p.next()
        peekables = [p for p in peekables if p]