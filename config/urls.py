import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

admin_url = os.environ.get("DJANGO_ADMIN_URL", "admin/").strip("/")
if not admin_url or any(part in {".", ".."} for part in admin_url.split("/")):
    raise ValueError("DJANGO_ADMIN_URL должен быть непустым путём без '..'.")

urlpatterns = [
    path(f"{admin_url}/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("projects/", include("portfolio.urls")),
    path("team/", include("team_board.urls")),
    path("events/", include("events.urls")),
    path(
        "complaints/",
        include(("core.complaint_urls", "core"), namespace="core"),
    ),
    path(
        "privacy/",
        TemplateView.as_view(template_name="core/privacy.html"),
        name="privacy",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
