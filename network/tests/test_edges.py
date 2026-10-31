from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from network.models import Edge, Node


class EdgeTests(APITestCase):
    def setUp(self):
        self.a = Node.objects.create(name="A")
        self.b = Node.objects.create(name="B")
        self.payload = {"source": "A", "destination": "B", "latency": 12.5}

    def test_create_list_duplicate_and_reverse(self):
        response = self.client.post("/edges", self.payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data["latency"]), 12.5)
        self.assertEqual(self.client.post("/edges", self.payload).status_code, 400)
        self.assertEqual(
            self.client.post(
                "/edges", {**self.payload, "source": "B", "destination": "A"}
            ).status_code,
            201,
        )
        with self.assertNumQueries(1):
            self.assertEqual(len(self.client.get("/edges").data), 2)

    def test_invalid_edges(self):
        cases = [
            {**self.payload, field: value}
            for field, value in [
                ("source", "missing"),
                ("destination", "missing"),
                ("source", "B"),
                ("latency", 0),
                ("latency", -1),
                ("latency", "NaN"),
                ("latency", "Infinity"),
                ("latency", "0.0000001"),
                ("latency", "abc"),
            ]
        ]
        cases += [
            {k: v for k, v in self.payload.items() if k != field}
            for field in self.payload
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/edges", payload).status_code, 400)

    def test_delete(self):
        edge = Edge.objects.create(source=self.a, destination=self.b, latency=1)
        self.assertEqual(self.client.delete(f"/edges/{edge.pk}").status_code, 204)
        self.assertEqual(self.client.delete(f"/edges/{edge.pk}").status_code, 404)

    def test_database_constraints(self):
        Edge.objects.create(source=self.a, destination=self.b, latency=1)
        for source, destination, latency in [
            (self.a, self.b, 1),
            (self.a, self.a, 1),
            (self.b, self.a, 0),
            (self.b, self.a, -1),
        ]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                Edge.objects.create(
                    source=source, destination=destination, latency=Decimal(latency)
                )
