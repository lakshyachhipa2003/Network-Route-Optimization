from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from network.models import Node


class NodeTests(APITestCase):
    def test_create_list_duplicate_and_invalid_names(self):
        response = self.client.post("/nodes", {"name": "ServerA"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {"id": response.data["id"], "name": "ServerA"})
        self.assertEqual(self.client.get("/nodes").data, [response.data])
        for payload in (
            {"name": "ServerA"},
            {},
            {"name": ""},
            {"name": "  "},
            {"name": "x" * 256},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/nodes", payload).status_code, 400)

    def test_delete(self):
        node = Node.objects.create(name="A")
        self.assertEqual(self.client.delete(f"/nodes/{node.pk}").status_code, 204)
        self.assertEqual(self.client.delete(f"/nodes/{node.pk}").status_code, 404)

    def test_database_constraints(self):
        Node.objects.create(name="A")
        for name in ("A", ""):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Node.objects.create(name=name)
