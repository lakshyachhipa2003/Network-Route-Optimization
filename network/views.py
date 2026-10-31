from django.db import IntegrityError, transaction
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Edge, Node, RouteHistory
from .serializers import (
    EdgeSerializer,
    HistoryFilterSerializer,
    NodeSerializer,
    NoPathSerializer,
    RouteHistorySerializer,
    RouteRequestSerializer,
    RouteResultSerializer,
)
from .services.route_optimizer import shortest_path

VALIDATION_ERROR = OpenApiResponse(
    description="Invalid input; field names map to lists of errors.",
    examples=[
        OpenApiExample(
            "Validation error", value={"source": ["This field is required."]}
        )
    ],
)


class IntegrityCreateMixin:
    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise serializers.ValidationError(
                "A duplicate or invalid record was submitted."
            ) from exc


@extend_schema(
    responses={201: NodeSerializer, 400: VALIDATION_ERROR},
    methods=["POST"],
    examples=[
        OpenApiExample("Node", value={"name": "ServerA"}, request_only=True),
        OpenApiExample(
            "Created node",
            value={"id": 1, "name": "ServerA"},
            response_only=True,
            status_codes=["201"],
        ),
    ],
)
class NodeListCreateView(IntegrityCreateMixin, generics.ListCreateAPIView):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer


@extend_schema(
    responses={201: EdgeSerializer, 400: VALIDATION_ERROR},
    methods=["POST"],
    examples=[
        OpenApiExample(
            "Edge",
            value={"source": "ServerA", "destination": "ServerB", "latency": 12.5},
            request_only=True,
        ),
        OpenApiExample(
            "Created edge",
            value={
                "id": 1,
                "source": "ServerA",
                "destination": "ServerB",
                "latency": 12.5,
            },
            response_only=True,
            status_codes=["201"],
        ),
    ],
)
class EdgeListCreateView(IntegrityCreateMixin, generics.ListCreateAPIView):
    queryset = Edge.objects.select_related("source", "destination")
    serializer_class = EdgeSerializer


@extend_schema(
    responses={204: None, 404: OpenApiResponse(description="Node not found")}
)
class NodeDeleteView(generics.DestroyAPIView):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer


@extend_schema(
    responses={204: None, 404: OpenApiResponse(description="Edge not found")}
)
class EdgeDeleteView(generics.DestroyAPIView):
    queryset = Edge.objects.all()
    serializer_class = EdgeSerializer


class ShortestRouteView(APIView):
    @extend_schema(
        request=RouteRequestSerializer,
        responses={
            200: RouteResultSerializer,
            400: VALIDATION_ERROR,
            404: NoPathSerializer,
        },
        examples=[
            OpenApiExample(
                "Route query",
                value={"source": "ServerA", "destination": "ServerD"},
                request_only=True,
            ),
            OpenApiExample(
                "Shortest route",
                value={
                    "total_latency": 23.4,
                    "path": ["ServerA", "ServerB", "ServerD"],
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Disconnected",
                value={"error": "No path exists between ServerA and ServerD"},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source"].name
        destination = serializer.validated_data["destination"].name
        edges = Edge.objects.order_by("id").values_list(
            "source__name", "destination__name", "latency"
        )
        result = shortest_path(edges, source, destination)
        if result is None:
            return Response(
                {"error": f"No path exists between {source} and {destination}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        latency, path = result
        history = RouteHistory.objects.create(
            source=source, destination=destination, total_latency=latency, path=path
        )
        return Response(RouteResultSerializer(history).data)


class RouteHistoryView(generics.ListAPIView):
    serializer_class = RouteHistorySerializer

    @extend_schema(
        parameters=[HistoryFilterSerializer],
        responses={200: RouteHistorySerializer(many=True), 400: VALIDATION_ERROR},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        serializer = HistoryFilterSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data.copy()
        limit = filters.pop("limit", None)
        if "date_from" in filters:
            filters["created_at__gte"] = filters.pop("date_from")
        if "date_to" in filters:
            filters["created_at__lte"] = filters.pop("date_to")
        queryset = RouteHistory.objects.filter(**filters)
        return queryset[:limit] if limit is not None else queryset
