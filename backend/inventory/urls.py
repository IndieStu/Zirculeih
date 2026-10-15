from django.urls import path

from . import views

urlpatterns = [
    path("", views.asset_list, name="asset_list"),
    path("uebersicht/", views.dashboard, name="inventory_dashboard"),
    path("lookup/", views.lookup, name="identifier_lookup"),
    path("neu/", views.asset_edit, name="asset_create"),
    path("standorte/", views.tree_view, {"kind": "locations"}, name="locations"),
    path("standorte/<uuid:node_id>/", views.tree_view, {"kind": "locations"}, name="location_edit"),
    path("kategorien/", views.tree_view, {"kind": "categories"}, name="categories"),
    path(
        "kategorien/<uuid:node_id>/", views.tree_view, {"kind": "categories"}, name="category_edit"
    ),
    path("namensraeume/", views.configuration, {"kind": "namespaces"}, name="inventory_namespaces"),
    path("zusatzfelder/", views.configuration, {"kind": "fields"}, name="inventory_fields"),
    path("schlagworte/", views.configuration, {"kind": "tags"}, name="inventory_tags"),
    path("import/", views.csv_import, name="csv_import"),
    path("import/<uuid:preview_id>/", views.csv_preview, name="csv_preview"),
    path("export/", views.csv_export, name="csv_export"),
    path("medien/<uuid:media_id>/", views.media_download, name="media_download"),
    path("medien/<uuid:media_id>/archivieren/", views.media_archive, name="media_archive"),
    path("assets/<uuid:asset_id>/", views.asset_detail, name="asset_detail"),
    path("assets/<uuid:asset_id>/bearbeiten/", views.asset_edit, name="asset_edit"),
    path("assets/<uuid:asset_id>/umziehen/", views.asset_move, name="asset_move"),
    path("assets/<uuid:asset_id>/archivieren/", views.asset_archive, name="asset_archive"),
    path("assets/<uuid:asset_id>/codes/neu/", views.identifier_add, name="identifier_add"),
    path(
        "assets/<uuid:asset_id>/codes/<uuid:identifier_id>/stilllegen/",
        views.identifier_retire,
        name="identifier_retire",
    ),
    path("assets/<uuid:asset_id>/zusatzfelder/", views.custom_value, name="custom_value"),
    path("assets/<uuid:asset_id>/hochladen/", views.media_upload, name="media_upload"),
]
