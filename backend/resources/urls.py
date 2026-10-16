from django.urls import path

from . import views

urlpatterns = [
    path("verwaltung/einweisungen/", views.qualifications_admin, name="qualifications_admin"),
    path(
        "verwaltung/<uuid:resource_id>/voraussetzungen/",
        views.requirements_edit,
        name="resource_requirements",
    ),
    path("", views.catalog, name="catalog"),
    path("verwaltung/", views.management, name="resources_manage"),
    path("verwaltung/neu/", views.edit, name="resource_create"),
    path("verwaltung/typen/<uuid:type_id>/", views.type_create, name="resource_type_edit"),
    path("verwaltung/typen/", views.type_create, name="resource_types"),
    path("verwaltung/<uuid:resource_id>/", views.manage_detail, name="resource_manage"),
    path("verwaltung/<uuid:resource_id>/bearbeiten/", views.edit, name="resource_edit"),
    path("verwaltung/<uuid:resource_id>/sichtbarkeit/", views.publish, name="resource_publish"),
    path("verwaltung/<uuid:resource_id>/einheiten/neu/", views.unit_edit, name="unit_create"),
    path(
        "verwaltung/<uuid:resource_id>/einheiten/<uuid:unit_id>/", views.unit_edit, name="unit_edit"
    ),
    path("verwaltung/<uuid:resource_id>/pools/neu/", views.pool_edit, name="pool_create"),
    path("verwaltung/<uuid:resource_id>/pools/<uuid:pool_id>/", views.pool_edit, name="pool_edit"),
    path(
        "verwaltung/<uuid:resource_id>/bilder/neu/",
        views.image_upload,
        name="resource_image_upload",
    ),
    path(
        "verwaltung/<uuid:resource_id>/einheiten/<uuid:unit_id>/codes/neu/",
        views.unit_code,
        name="unit_code",
    ),
    path(
        "verwaltung/<uuid:resource_id>/einheiten/<uuid:unit_id>/codes/<uuid:identifier_id>/stilllegen/",
        views.unit_code,
        name="unit_code_retire",
    ),
    path("bilder/<uuid:image_id>/", views.image, name="resource_image"),
    path("bilder/<uuid:image_id>/archivieren/", views.image_archive, name="resource_image_archive"),
    path("<slug:slug>/", views.detail, name="resource_detail"),
]
