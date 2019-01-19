"""
A basic graph datastructure
"""
from typing import (
    Callable,
    Dict,
    Generic,
    Iterator,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

from typing_extensions import Protocol


class GraphNode(Protocol):
    @property
    def identifier(self) -> str:
        ...  # pragma: nocover


# The graph is generic for the types of nodes and edges,
# mostly to make it easier to type-check code using the graph.
NODE_TYPE = TypeVar("NODE_TYPE", bound=GraphNode)
EDGE_TYPE = TypeVar("EDGE_TYPE")


class ObjectGraph(Generic[NODE_TYPE, EDGE_TYPE]):
    """
    A basic graph datastructure where the nodes can be arbitrary objects
    with an attribute named "identifier". Edges between nodes can have
    associated data.
    """

    def __init__(self):
        self._roots: Set[str] = set()
        self._nodes: Dict[str, NODE_TYPE] = {}
        self._edges: Dict[Tuple[str, str], EDGE_TYPE] = {}

    def __repr__(self):
        return f"<{type(self).__name__} with {len(self._roots)} roots, {len(self._nodes)} nodes and {len(self._edges)} edges>"  # noqa:E501

    def roots(self) -> Iterator[NODE_TYPE]:
        """
        Yield the roots of the graph
        """
        return (self._nodes[identifier] for identifier in self._roots)

    def nodes(self) -> Iterator[NODE_TYPE]:
        """
        Yield all nodes in an arbirary order
        """
        return iter(self._nodes.values())

    def edges(self) -> Iterator[Tuple[NODE_TYPE, NODE_TYPE, EDGE_TYPE]]:
        for from_id, to_id in self._edges:
            yield self._nodes[from_id], self._nodes[to_id], self._edges[
                (from_id, to_id)
            ]

    def add_root(self, node: Union[str, NODE_TYPE]):
        value = self.find_node(node)
        if value is None:
            raise KeyError("Adding non-existing {node!r} as root")

        self._roots.add(value.identifier)

    def add_node(self, node: NODE_TYPE):
        if node.identifier in self._nodes:
            raise ValueError(f"Already have node with name {node.identifier!r}")

        self._nodes[node.identifier] = node

    def add_edge(
        self,
        source: NODE_TYPE,
        destination: NODE_TYPE,
        edge_attributes: EDGE_TYPE,
        merge_attributes: Optional[Callable[[EDGE_TYPE, EDGE_TYPE], EDGE_TYPE]] = None,
    ):
        """
        Add a directed edge between *source* and *destination* with optional edge
        attributes.

        It is an error to add an already existing edge unless *merge_attributes*
        is specified.
        """
        from_node = self.find_node(source)
        to_node = self.find_node(destination)
        if from_node is None:
            raise KeyError("Source {source!r} not found")
        if to_node is None:
            raise KeyError("Destination {destination!r} not found")

        key = (from_node.identifier, to_node.identifier)
        try:
            current_edge = self._edges[key]

        except KeyError:
            self._edges[key] = edge_attributes

        else:
            if merge_attributes is not None:
                self._edges[key] = merge_attributes(current_edge, edge_attributes)

            else:
                raise ValueError(
                    f"Edge between {from_node.identifier!r} and {to_node.identifier!r} already exists"  # noqa:E501
                )

    def find_node(self, node: Union[str, NODE_TYPE]) -> Optional[NODE_TYPE]:
        """ Find *node* in the graph, return the graph node or None """
        if isinstance(node, str):
            return self._nodes.get(node)

        else:
            return self._nodes.get(node.identifier)

    def __contains__(self, node: Union[str, NODE_TYPE]):
        return self.find_node(node) is not None

    def edge_data(
        self, source: Union[str, NODE_TYPE], destination: Union[str, NODE_TYPE]
    ) -> EDGE_TYPE:
        """
        Return the data associated with the edge between *source* and *destination*.

        Raises *ValueError* when there is no such edge.
        """
        from_node = self.find_node(source)
        to_node = self.find_node(destination)
        if from_node is None:
            raise KeyError("Source {source!r} not found")
        if to_node is None:
            raise KeyError("Destination {destination!r} not found")

        try:
            return self._edges[(from_node.identifier, to_node.identifier)]
        except KeyError:
            raise KeyError(
                f"There is no edge between {from_node.identifier} and {to_node.identifier}"  # noqa:E501
            ) from None

    def outgoing(
        self, source: Union[str, NODE_TYPE]
    ) -> Iterator[Tuple[EDGE_TYPE, NODE_TYPE]]:
        """
        Yield (edge, node) for all outgoing edges
        """
        node = self.find_node(source)
        if node is None:
            return

        for from_node, to_node in self._edges:
            if from_node == node.identifier:
                yield self._edges[(from_node, to_node)], self._nodes[to_node]

    def incoming(
        self, destination: Union[str, NODE_TYPE]
    ) -> Iterator[Tuple[EDGE_TYPE, NODE_TYPE]]:
        """
        Yield (edge, node) for all incoming edges
        """
        node = self.find_node(destination)
        if node is None:
            return

        for from_node, to_node in self._edges:
            if to_node == node.identifier:
                yield self._edges[(from_node, to_node)], self._nodes[from_node]

    def iter_graph(
        self, *, node: Union[str, NODE_TYPE] = None, _visited: Optional[set] = None
    ) -> Iterator[NODE_TYPE]:
        """
        Yield all nodes in the graph reachable from *node*
        or any of the graph roots.
        """
        if _visited is None:
            _visited = set()

        if node is None:
            for node in self._roots:
                yield from self.iter_graph(node=node, _visited=_visited)

        else:
            start_node = self.find_node(node)
            if start_node is None:
                raise KeyError(f"Start node {node!r} not found")

            if start_node.identifier in _visited:
                return

            _visited.add(start_node.identifier)
            yield start_node

            for _, node in self.outgoing(start_node):
                yield from self.iter_graph(node=node, _visited=_visited)
