import collections
from typing import Callable, Dict, List, Set, Tuple

from ._nodes import BaseNode

WaitForCallback = Callable[[BaseNode, BaseNode], None]


class DependentProcessor:
    def __init__(self):
        self._waiting: Dict[
            str, List[Tuple[BaseNode, BaseNode, WaitForCallback]]
        ] = collections.defaultdict(list)
        self._finished: Set[str] = set()
        self._finished_q: List[str] = []

    def __repr__(self):
        return f"<DependentProcessor #finished_q={len(self._finished_q)} #waiting={len(self._waiting)}>"  # noqa: B950

    @property
    def has_unfinished(self):
        return self._finished_q or self._waiting

    def wait_for(
        self, node: BaseNode, other: BaseNode, callback: WaitForCallback
    ) -> None:
        self._waiting[other.identifier].append((node, other, callback))
        if self.is_finished(other):
            self.finished(other)

    def finished(self, node: BaseNode):
        self._finished_q.append(node.identifier)

    def have_finished_work(self):
        return len(self._finished_q) != 0

    def process_finished_nodes(self):
        while self._finished_q:
            identifier = self._finished_q.pop()
            if identifier in self._waiting:
                callbacks = self._waiting.pop(identifier)
                for (n1, n2, callback) in callbacks:
                    callback(n1, n2)

            assert identifier not in self._waiting
            self._finished.add(identifier)

    def is_finished(self, node):
        return node.identifier in self._finished
