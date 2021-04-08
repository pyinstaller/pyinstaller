from typing import Callable, Generic, List, TypeVar, cast

T = TypeVar("T", bound=Callable)


def as_T(function):
    """
    MyPy helper: cast *function* to type *T*.

    This is used to give the *__call__* attribute
    of :class:`CallbackList` and :class:`FirstNotNone`
    the right type.

    Args:
      function: Function to cast to type *T*
    """
    return cast(T, function)


class CallbackList(Generic[T]):
    """
    A sequence of callbacks that are called
    in reverse order of insertion.

    The class is a generic type with the
    type of the callback functions as the
    type parameter.
    """

    _callbacks: List[T]

    def __init__(self):
        self._callbacks = []

    def add(self, function: T):
        """
        Add a *function* to the callback list.

        Args:
          function: Function to be added
        """
        self._callbacks.insert(0, function)

    def clear(self):
        """
        Clear the callback list
        """

        del self._callbacks[:]

    @as_T
    def __call__(self, *args, **kwds):
        """
        Call every callback in the callback
        list with the given arguments. The
        callbacks are called in reverse order
        of inserting.

        The result of the called functions is
        ignored.

        Args:
          args: Positional arguments for the function
          kwds: Keyword arguments for the function
        """
        for function in self._callbacks:
            function(*args, **kwds)


class FirstNotNone(Generic[T]):
    """
    A sequence of callbacks that are called
    in reverse order of insertion, and where
    the first result is used.

    The class is a generic type with the
    type of the callback functions as the
    type parameter.
    """

    _callbacks: List[T]

    def __init__(self):
        self._callbacks = []

    def add(self, function: T):
        """
        Add *function* to the callback list

        Args:
          function: Function to add to the list
        """
        self._callbacks.insert(0, function)

    def clear(self):
        """
        Clear the callback list
        """
        del self._callbacks[:]

    @as_T
    def __call__(self, *args, **kwds):
        """
        Call the functions in the callback list
        in reverse order of addition. Return the
        first result that is not :data:`None`.

        Args:
          args: Posititional arguments for the callback
          kwds: Keyword arguments for the callback

        Returns:
          The first not :data:`None` result or :data:`None`
        """
        for function in self._callbacks:
            result = function(*args, **kwds)
            if result is not None:
                return result

        return None
