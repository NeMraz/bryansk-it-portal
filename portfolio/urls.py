from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("my/", views.my_projects, name="my"),
    path("moderation/", views.moderation_queue, name="moderation"),
    path("create/", views.project_create, name="create"),
    path("<int:pk>/comment/", views.comment_create, name="comment_create"),
    path("comments/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
    path("<int:pk>/vote/", views.vote_toggle, name="vote"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_edit, name="edit"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
    path("<int:pk>/moderate/", views.moderate_project, name="moderate"),
]
