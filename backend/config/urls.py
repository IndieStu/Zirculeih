from django.urls import include, path

from . import views

urlpatterns = [
    path("konto/", include("accounts.urls")),
    path("", views.home, name="home"),
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
