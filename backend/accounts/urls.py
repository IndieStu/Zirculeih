from django.urls import path

from . import oidc, views

urlpatterns = [
    path("", views.account, name="account"),
    path("registrieren/", views.signup, name="signup"),
    path("anmelden/", views.sign_in, name="login"),
    path("abmelden/", views.sign_out, name="logout"),
    path("datenschutz/", views.privacy, name="privacy"),
    path("link/<str:purpose>/", views.token_request, name="token_request"),
    path("bestaetigen/<str:raw>/", views.token_consume, {"purpose": "verify"}, name="verify"),
    path("passwort-neu/<str:raw>/", views.token_consume, {"purpose": "reset"}, name="reset"),
    path("passwort/", views.password_change, name="password_change"),
    path("gruppen/", views.groups, name="groups"),
    path("gruppen/neu/", views.group_edit, name="group_create"),
    path("gruppen/<uuid:group_id>/", views.group_detail, name="group_detail"),
    path("gruppen/<uuid:group_id>/bearbeiten/", views.group_edit, name="group_edit"),
    path("gruppen/<uuid:group_id>/archivieren/", views.group_archive, name="group_archive"),
    path(
        "gruppen/<uuid:group_id>/grants/<int:grant_id>/entfernen/",
        views.grant_remove,
        name="grant_remove",
    ),
    path("kontosperre/<uuid:user_id>/", views.suspension, name="suspension"),
    path("oidc/start/", oidc.sign_in, name="oidc_login"),
    path("oidc/trennen/", views.oidc_unlink, name="oidc_unlink"),
    path("oidc/verbinden/", oidc.link, name="oidc_link"),
    path("oidc/callback/", oidc.callback, name="oidc_callback"),
]
