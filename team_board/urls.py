from django.urls import path

from . import views

app_name = "team_board"

urlpatterns = [
    path("", views.post_list, name="list"),
    path("my/", views.my_posts, name="my"),
    path("moderation/", views.moderation_queue, name="moderation"),
    path("create/", views.post_create, name="create"),
    path("<int:pk>/", views.post_detail, name="detail"),
    path("<int:pk>/edit/", views.post_edit, name="edit"),
    path("<int:pk>/toggle/", views.post_toggle_open, name="toggle"),
    path("<int:pk>/delete/", views.post_delete, name="delete"),
    path("<int:pk>/moderate/", views.moderate_post, name="moderate"),
    path("<int:pk>/respond/", views.response_create, name="respond"),
]
