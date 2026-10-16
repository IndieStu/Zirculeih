from django.urls import path

from . import views

urlpatterns = [
    path("betrieb/nicht-abgeholt/<uuid:booking_id>/", views.no_show, name="loan_no_show"),
    path(
        "betrieb/zuordnung/<int:assignment_id>/entfernen/",
        views.unassign,
        name="agreement_unassign",
    ),
    path("", views.own, name="own_loans"),
    path("vereinbarungen/", views.agreement_list, name="lending_agreements"),
    path("betrieb/", views.operations, name="loan_operations"),
    path("betrieb/ausgabe/", views.checkout, name="loan_checkout"),
    path("betrieb/ruecknahme/", views.return_scan, name="loan_return_scan"),
    path("betrieb/vereinbarungen/", views.agreement_admin, name="agreement_admin"),
    path(
        "betrieb/vereinbarungen/<uuid:agreement_id>/version/",
        views.version_add,
        name="agreement_version_add",
    ),
    path(
        "betrieb/version/<uuid:version_id>/veroeffentlichen/",
        views.version_publish,
        name="agreement_publish",
    ),
    path("betrieb/zuordnung/", views.assignment, name="agreement_assignment"),
    path("position/<uuid:line_id>/ruecknahme/", views.line_return, name="loan_return"),
    path("position/<uuid:line_id>/verlaengern/", views.extend, name="loan_extend"),
    path("<uuid:loan_id>/", views.detail, name="loan_detail"),
]
