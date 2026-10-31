from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Node(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=~Q(name=""), name="node_name_not_empty")
        ]

    def __str__(self):
        return self.name


class Edge(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="outgoing")
    destination = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="incoming"
    )
    latency = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "destination"], name="unique_directed_edge"
            ),
            models.CheckConstraint(
                condition=~Q(source=F("destination")), name="edge_no_self_loop"
            ),
            models.CheckConstraint(
                condition=Q(latency__gt=0), name="edge_positive_latency"
            ),
        ]


class RouteHistory(models.Model):
    # Snapshots intentionally survive deletion and recreation of graph nodes.
    source = models.CharField(max_length=255, db_index=True)
    destination = models.CharField(max_length=255, db_index=True)
    total_latency = models.DecimalField(max_digits=30, decimal_places=6)
    path = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["source", "destination", "-created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_latency__gte=0), name="route_nonnegative_latency"
            )
        ]
