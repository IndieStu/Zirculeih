from django.urls import path

from . import views

urlpatterns = [
    path("inventur/", views.runs, name="inventory_runs"),
    path("inventur/<uuid:run_id>/", views.run_detail, name="inventory_run"),
    path("inventur/<uuid:run_id>/export/", views.run_export, name="inventory_run_export"),
    path("abweichungen/<uuid:discrepancy_id>/", views.discrepancy, name="inventory_discrepancy"),
    path("wartung/", views.maintenance, name="maintenance"),
    path("wartung/<uuid:task_id>/", views.task, name="maintenance_task"),
    path("sammelaktion/", views.bulk, name="asset_bulk"),
    path("berichte/", views.reporting, name="asset_reports"),
    path("etiketten/", views.labels, name="asset_labels"),
    path("etiketten/<uuid:identifier_id>.svg", views.label_svg, name="asset_label_svg"),
    path("terminal/", views.terminal_home, name="staffed_terminal"),
    path("terminal/scan/", views.terminal_scan, name="terminal_scan"),
]
