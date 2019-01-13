from ._nodes import BaseNode
import collections
from typing import Tuple, List, Set, Callable, Dict

WaitForCallback = Callable[[BaseNode, BaseNode], None]


class DependentProcessor:
    """ XXX: Document me """

    def __init__(self):
        self._waiting: Dict[
            str, List[Tuple[BaseNode, BaseNode, WaitForCallback]]
        ] = collections.defaultdict(list)
        self._finished: Set[str] = set()
        self._finished_q: List[str] = []
        self._depcount: Dict[str, int] = collections.defaultdict(int)

    def inc_depcount(self, node):
        self._depcount[node.identifier] += 1

    def dec_depcount(self, node):
        self._depcount[node.identifier] -= 1
        if not self._depcount[node.identifier]:
            self.finished(node)

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
