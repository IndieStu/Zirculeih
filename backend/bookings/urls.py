from django.urls import path

from . import views

urlpatterns = [
    path("", views.own, name="own_bookings"),
    path("neu/<uuid:resource_id>/", views.create, name="booking_create"),
    path("betrieb/", views.operations, name="booking_operations"),
    path("betrieb/regeln/<uuid:resource_id>/", views.policy_edit, name="booking_policy"),
    path("betrieb/zeitfenster/neu/", views.schedule_add, name="schedule_add"),
    path(
        "betrieb/ausnahmen/neu/",
        views.schedule_add,
        {"exception": True},
        name="schedule_exception_add",
    ),
    path(
        "betrieb/zeitfenster/<uuid:row_id>/entfernen/",
        views.schedule_remove,
        name="schedule_remove",
    ),
    path(
        "betrieb/ausnahmen/<uuid:row_id>/entfernen/",
        views.schedule_remove,
        {"exception": True},
        name="schedule_exception_remove",
    ),
    path("betrieb/sperren/neu/", views.block_add, name="booking_block"),
    path("betrieb/sperren/<uuid:block_id>/aufheben/", views.block_lift, name="booking_block_lift"),
    path(
        "betrieb/hinweise/<uuid:incident_id>/",
        views.incident_resolve,
        name="booking_incident_resolve",
    ),
    path("<uuid:booking_id>/", views.detail, name="booking_detail"),
    path("<uuid:booking_id>/stornieren/", views.cancel, name="booking_cancel"),
]
