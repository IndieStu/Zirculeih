from django.urls import path

from . import views

urlpatterns = [
    path("", views.month, name="personal_calendar"),
    path("abos/", views.feeds, name="calendar_feeds"),
    path("abo/<str:raw>.ics", views.subscription, name="calendar_subscription"),
    path("nachrichten/", views.preferences, name="notification_preferences"),
    path("verwaltung/", views.administration, name="notification_admin"),
]
