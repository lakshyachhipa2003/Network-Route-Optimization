from decimal import Decimal as D

from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from network.models import Edge, Node, RouteHistory
from network.services.route_optimizer import shortest_path


class AlgorithmTests(SimpleTestCase):
    def test_direct(self):
        self.assertEqual(
            shortest_path([("A", "B", D("12.5"))], "A", "B"), (D("12.5"), ["A", "B"])
        )

    def test_indirect_decimal_route_and_cycle(self):
        edges = [
            ("A", "D", D(9)),
            ("A", "B", D("0.1")),
            ("B", "D", D("0.2")),
            ("B", "A", D(1)),
            ("A", "C", D(1)),
            ("C", "D", D(1)),
        ]
        self.assertEqual(shortest_path(edges, "A", "D"), (D("0.3"), ["A", "B", "D"]))

    def test_disconnected_and_direction(self):
        edges = [("A", "B", D(1)), ("C", "D", D(1))]
        self.assertIsNone(shortest_path(edges, "A", "D"))
        self.assertIsNone(shortest_path(edges, "B", "A"))
        self.assertIsNone(shortest_path([], "A", "B"))

    def test_same_node(self):
        self.assertEqual(shortest_path([], "A", "A"), (D(0), ["A"]))

    def test_parallel_edges_and_equal_paths(self):
        edges = [
            ("A", "B", D(9)),
            ("A", "B", D(1)),
            ("B", "D", D(1)),
            ("A", "C", D(1)),
            ("C", "D", D(1)),
        ]
        latency, path = shortest_path(edges, "A", "D")
        self.assertEqual(latency, D(2))
        self.assertIn(path, [["A", "B", "D"], ["A", "C", "D"]])

    def test_large_graph(self):
        edges = [(str(i), str(i + 1), D(1)) for i in range(5000)]
        edges += [(str(i), str(i + 2), D(3)) for i in range(4999)]
        latency, path = shortest_path(edges, "0", "5000")
        self.assertEqual(latency, D(5000))
        self.assertEqual(len(path), 5001)

    def test_invalid_weights(self):
        for weight in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                shortest_path([("A", "B", D(weight))], "A", "B")


class RouteAPITests(APITestCase):
    def setUp(self):
        self.a, self.b, self.c = [Node.objects.create(name=name) for name in "ABC"]
        Edge.objects.create(source=self.a, destination=self.b, latency=D("0.1"))
        Edge.objects.create(source=self.b, destination=self.c, latency=D("0.2"))
        Edge.objects.create(source=self.a, destination=self.c, latency=9)

    def test_shortest_and_history(self):
        response = self.client.post(
            "/routes/shortest", {"source": "A", "destination": "C"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"total_latency": 0.3, "path": ["A", "B", "C"]}
        )
        self.assertEqual(RouteHistory.objects.get().total_latency, D("0.3"))

    def test_no_path(self):
        response = self.client.post(
            "/routes/shortest", {"source": "C", "destination": "A"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"error": "No path exists between C and A"})
        self.assertFalse(RouteHistory.objects.exists())

    def test_same_node(self):
        response = self.client.post(
            "/routes/shortest", {"source": "A", "destination": "A"}
        )
        self.assertEqual(response.json(), {"total_latency": 0, "path": ["A"]})
        self.assertEqual(RouteHistory.objects.count(), 1)

    def test_invalid_nodes(self):
        for payload in (
            {},
            {"source": "A"},
            {"source": "missing", "destination": "A"},
            {"source": "A", "destination": "missing"},
        ):
            self.assertEqual(
                self.client.post("/routes/shortest", payload).status_code, 400
            )
        self.assertFalse(RouteHistory.objects.exists())
