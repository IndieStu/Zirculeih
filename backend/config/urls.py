from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/live/", views.live, name="live"),
    path("health/ready/", views.ready, name="ready"),
]
