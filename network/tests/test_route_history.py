from datetime import datetime, timezone

from rest_framework.test import APITestCase

from network.models import Edge, Node, RouteHistory


class HistoryTests(APITestCase):
    def setUp(self):
        self.first = RouteHistory.objects.create(
            source="A", destination="B", total_latency=1, path=["A", "B"]
        )
        self.second = RouteHistory.objects.create(
            source="B", destination="C", total_latency=2, path=["B", "C"]
        )
        RouteHistory.objects.filter(pk=self.first.pk).update(
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        RouteHistory.objects.filter(pk=self.second.pk).update(
            created_at=datetime(2026, 2, 1, tzinfo=timezone.utc)
        )

    def test_order_and_combined_filters(self):
        with self.assertNumQueries(1):
            response = self.client.get("/routes/history")
        self.assertEqual(
            [row["id"] for row in response.data], [self.second.pk, self.first.pk]
        )
        response = self.client.get(
            "/routes/history",
            {
                "source": "A",
                "destination": "B",
                "limit": 1,
                "date_from": "2026-01-01T00:00:00Z",
                "date_to": "2026-01-01T00:00:00Z",
            },
        )
        self.assertEqual([row["id"] for row in response.data], [self.first.pk])

    def test_individual_filters(self):
        for params, expected in [
            ({"source": "B"}, self.second.pk),
            ({"destination": "B"}, self.first.pk),
            ({"limit": 1}, self.second.pk),
            ({"date_from": "2026-02-01T00:00:00Z"}, self.second.pk),
            ({"date_to": "2026-01-01T00:00:00Z"}, self.first.pk),
        ]:
            with self.subTest(params=params):
                self.assertEqual(
                    [
                        row["id"]
                        for row in self.client.get("/routes/history", params).data
                    ],
                    [expected],
                )
        self.assertEqual(
            self.client.get("/routes/history", {"source": "unknown"}).data, []
        )

    def test_invalid_filters(self):
        for params in [{"limit": value} for value in (0, -1, "abc", "1.5", 10001)] + [
            {"date_from": "bad"},
            {"date_to": "bad"},
            {"date_from": "2026-02-01T00:00:00Z", "date_to": "2026-01-01T00:00:00Z"},
        ]:
            with self.subTest(params=params):
                self.assertEqual(
                    self.client.get("/routes/history", params).status_code, 400
                )

    def test_history_survives_graph_deletion(self):
        a, b = [Node.objects.create(name=name) for name in "AB"]
        edge = Edge.objects.create(source=a, destination=b, latency=1)
        self.client.post("/routes/shortest", {"source": "A", "destination": "B"})
        self.client.delete(f"/edges/{edge.pk}")
        self.assertEqual(RouteHistory.objects.count(), 3)
        Edge.objects.create(source=a, destination=b, latency=2)
        self.client.delete(f"/nodes/{a.pk}")
        self.assertFalse(Edge.objects.exists())
        self.assertEqual(RouteHistory.objects.count(), 3)
        self.assertEqual(
            self.client.get("/routes/history", {"source": "A"}).status_code, 200
        )

    def test_schema_and_swagger(self):
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
