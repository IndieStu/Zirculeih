from django.urls import path

from . import api, schema

urlpatterns = [
    path("openapi.json", schema.view, name="api_schema"),
    path("", api.endpoint),
    path("<path:endpoint>", api.endpoint),
]
