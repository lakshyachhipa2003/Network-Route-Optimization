from django.contrib import admin

from .models import Edge, Node, RouteHistory

admin.site.register(Node)
admin.site.register(Edge)


@admin.register(RouteHistory)
class RouteHistoryAdmin(admin.ModelAdmin):
    list_display = ["source", "destination", "total_latency", "created_at"]
    readonly_fields = [field.name for field in RouteHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
