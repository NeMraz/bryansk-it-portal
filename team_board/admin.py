from django.contrib import admin

from .models import Response, TeamPost


@admin.register(TeamPost)
class TeamPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "is_open", "created_at")
    list_filter = ("status", "is_open")
    search_fields = ("title", "description", "author__username")


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "created_at")
    search_fields = ("message", "author__username", "post__title")
