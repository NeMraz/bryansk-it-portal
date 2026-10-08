from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "starts_at", "place", "is_published")
    list_filter = ("event_type", "is_published")
    search_fields = ("title", "description", "place")
    date_hierarchy = "starts_at"
