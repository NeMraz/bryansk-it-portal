from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.report_queue, name="reports"),
    path("report/<slug:kind>/<int:pk>/", views.report_create, name="report"),
    path("<int:pk>/handle/", views.report_handle, name="report_handle"),
]
