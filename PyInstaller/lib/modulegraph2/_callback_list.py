from typing import Callable, Generic, List, TypeVar, cast

T = TypeVar("T", bound=Callable)


def as_T(function):
    return cast(T, function)


class CallbackList(Generic[T]):
    _callbacks: List[T]

    def __init__(self):
        self._callbacks = []

    def add(self, function: T):
        self._callbacks.insert(0, function)

    def clear(self):
        del self._callbacks[:]

    @as_T
    def __call__(self, *args, **kwds):
        for function in self._callbacks:
            function(*args, **kwds)


class FirstNotNone(Generic[T]):
    _callbacks: List[T]

    def __init__(self):
        self._callbacks = []

    def add(self, function: T):
        self._callbacks.insert(0, function)

    def clear(self):
        del self._callbacks[:]

    @as_T
    def __call__(self, *args, **kwds):
        for function in self._callbacks:
            result = function(*args, **kwds)
            if result is not None:
                return result

        return None
