from django.conf import settings
from django.urls import include, path
from integrations.views import management

from . import views

urlpatterns = [
    path("api/v1/", include("integrations.urls")),
    path("konto/integrationen/", management, name="integrations_manage"),
    path("betrieb/", include("assetops.urls")),
    path("kalender/", include("notifications.urls")),
    path("ausleihen/", include("lending.urls")),
    path("buchungen/", include("bookings.urls")),
    path("entdecken/", include("resources.urls")),
    path("inventar/", include("inventory.urls")),
    path("konto/", include("accounts.urls")),
    path("", views.home, name="home"),
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]


# Review only: serve collected, read-only public assets without requiring a new proxy.

if settings.REVIEW_MODE:
    from django.views.static import serve

    urlpatterns += [path("static/<path:path>", serve, {"document_root": settings.STATIC_ROOT})]
