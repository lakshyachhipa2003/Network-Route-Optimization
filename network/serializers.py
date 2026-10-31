from rest_framework import serializers

from .models import Edge, Node, RouteHistory


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ["id", "name"]
        read_only_fields = ["id"]


class EdgeSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )
    destination = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )

    class Meta:
        model = Edge
        fields = ["id", "source", "destination", "latency"]
        read_only_fields = ["id"]
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Edge.objects.all(), fields=["source", "destination"]
            )
        ]

    def validate(self, attrs):
        if attrs["source"] == attrs["destination"]:
            raise serializers.ValidationError("Self-connections are not allowed.")
        return attrs


class RouteRequestSerializer(serializers.Serializer):
    source = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )
    destination = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )


class RouteResultSerializer(serializers.Serializer):
    total_latency = serializers.DecimalField(max_digits=30, decimal_places=6)
    path = serializers.ListField(child=serializers.CharField())


class RouteHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteHistory
        fields = ["id", "source", "destination", "total_latency", "path", "created_at"]


class HistoryFilterSerializer(serializers.Serializer):
    source = serializers.CharField(required=False, max_length=255)
    destination = serializers.CharField(required=False, max_length=255)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=10000)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if (
            "date_from" in attrs
            and "date_to" in attrs
            and attrs["date_from"] > attrs["date_to"]
        ):
            raise serializers.ValidationError(
                "date_from must be before or equal to date_to."
            )
        return attrs


class NoPathSerializer(serializers.Serializer):
    error = serializers.CharField()
