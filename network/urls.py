from django.urls import path

from . import views

urlpatterns = [
    path("nodes", views.NodeListCreateView.as_view(), name="nodes"),
    path("nodes/<int:pk>", views.NodeDeleteView.as_view(), name="node-detail"),
    path("edges", views.EdgeListCreateView.as_view(), name="edges"),
    path("edges/<int:pk>", views.EdgeDeleteView.as_view(), name="edge-detail"),
    path("routes/shortest", views.ShortestRouteView.as_view(), name="shortest-route"),
    path("routes/history", views.RouteHistoryView.as_view(), name="route-history"),
]
