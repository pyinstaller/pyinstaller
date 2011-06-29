"""
Python 2.4-like compatibility library for Python 2.3
"""
from itertools import izip, imap
try:
    from itertools import tee, groupby

except ImportError:
    pass

#
# builtins from 2.4
#

try:
    set, frozenset
except NameError:
    from sets import Set as set, ImmutableSet as frozenset

try:
    sorted
except NameError:
    def sorted(iterable, cmp=None, key=None, reverse=False):
        if key is not None:
            a, b = tee(iterable)
            iterable = izip(imap(key, iterable), iterable)
        if cmp is not None:
            iterable = list(iterable)
            iterable.sort(cmp)
        else:
            iterable = isorted(iterable)
        if key is not None:
            iterable = [v for (k,v) in iterable]
        if type(iterable) is not list:
            iterable = list(iterable)
        if reverse:
            iterable.reverse()
        return iterable

try:
    reversed
except NameError:
    def reversed(iterable):
        lst = list(iterable)
        pop = lst.pop
        while lst:
            yield pop()


#
# itertools functions from 2.4
#
try:
    tee
except NameError:
    def tee(iterable, n=2):
        def gen(next, data={}, cnt=[0]):
            for i in count():
                if i == cnt[0]:
                    item = data[i] = next()
                    cnt[0] += 1
                else:
                    item = data.pop(i)
                yield item
        return tuple(imap(gen, repeat(iter(iterable), n)))

try:
    groupby
except NameError:
    class groupby(object):
        def __init__(self, iterable, key=None):
            if key is None:
                key = lambda x: x
            self.keyfunc = key
            self.it = iter(iterable)
            self.tgtkey = self.currkey = self.currvalue = xrange(0)
        def __iter__(self):
            return self
        def next(self):
            while self.currkey == self.tgtkey:
                self.currvalue = self.it.next() # Exit on StopIteration
                self.currkey = self.keyfunc(self.currvalue)
            self.tgtkey = self.currkey
            return (self.currkey, self._grouper(self.tgtkey))
        def _grouper(self, tgtkey):
            while self.currkey == tgtkey:
                yield self.currvalue
                self.currvalue = self.it.next() # Exit on StopIteration
                self.currkey = self.keyfunc(self.currvalue)


#
# operators from 2.4
#
try:
    from operator import attrgetter, itemgetter
except ImportError:
    def attrgetter(attr):
        def attrgetter(obj):
            return getattr(obj, attr)
        return attrgetter

    def itemgetter(item):
        def itemgetter(obj):
            return obj[item]
        return itemgetter


#
# deque from 2.4's collections
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/259179/
#
try:
    from collections import deque
except ImportError:
    class deque(object):

        def __init__(self, iterable=()):
            self.data = dict(enumerate(iterable))
            self.left = 0
            self.right = len(self.data)

        def append(self, x):
            self.data[self.right] = x
            self.right += 1

        def appendleft(self, x):
            self.left -= 1
            self.data[self.left] = x

        def pop(self):
            if self.left == self.right:
                raise IndexError('cannot pop from empty deque')
            self.right -= 1
            return self.data[self.right]

        def popleft(self):
            if self.left == self.right:
                raise IndexError('cannot pop from empty deque')
            x = self.data[self.left]
            self.left += 1
            return x

        def __len__(self):
            return self.right - self.left

        def __iter__(self):
            return imap(self.data.__getitem__, xrange(self.left, self.right))

        def __repr__(self):
            return 'deque(%r)' % (list(self),)

        def __getstate__(self):
            return (tuple(self),)

        def __setstate__(self, s):
            self.__init__(s[0])

        def __hash__(self):
            raise TypeError

        def __copy__(self):
            return self.__class__(self)

        def __deepcopy__(self, memo={}):
            from copy import deepcopy
            result = self.__class__()
            memo[id(self)] = result
            result.__init__(deepcopy(tuple(self), memo))
            return result

#
# new functions
#
import heapq as _heapq
def isorted(iterable):
    lst = list(iterable)
    _heapq.heapify(lst)
    pop = _heapq.heappop
    while lst:
        yield pop(lst)

def ireversed(iterable):
    if isinstance(iterable, (list, tuple)):
        for i in xrange(len(iterable)-1, -1, -1):
            yield iterable[i]
    else:
        for obj in reversed(iterable):
            yield obj
