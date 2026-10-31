"""Dijkstra over directed edges with exact decimal arithmetic."""

from collections import defaultdict
from decimal import Decimal
from heapq import heappop, heappush
from typing import Iterable


def shortest_path(
    edges: Iterable[tuple[str, str, Decimal]],
    source: str,
    destination: str,
) -> tuple[Decimal, list[str]] | None:
    """Return minimum latency and path, or None; caller validates node existence.

    Lazy heap: O((V + E) log(V + E)) time and O(V + E) space.
    Equal-cost ties retain the first discovered predecessor.
    """
    adjacency = defaultdict(list)
    for start, end, latency in edges:
        if not latency.is_finite() or latency <= 0:
            raise ValueError("Edge latency must be finite and positive")
        adjacency[start].append((end, latency))
    distances = {source: Decimal(0)}
    previous = {}
    queue = [(Decimal(0), source)]
    while queue:
        distance, node = heappop(queue)
        if distance != distances[node]:
            continue
        if node == destination:
            path = [node]
            while node != source:
                node = previous[node]
                path.append(node)
            return distance, list(reversed(path))
        for neighbor, latency in adjacency[node]:
            candidate = distance + latency
            if neighbor not in distances or candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = node
                heappush(queue, (candidate, neighbor))
    return None
