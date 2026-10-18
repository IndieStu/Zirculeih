from accounts.authorization import require
from accounts.ratelimit import take
from accounts.views import throttled
from assetops.views import page
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import forms, services
from .models import IntegrationClient, IntegrationToken


@page
@require_http_methods(["GET", "POST"])
def management(request):
    require(request.user, "integration.manage")
    action = request.POST.get("action")
    client_form = forms.ClientForm(
        request.user, request.POST if action == "client" else None, auto_id="id_integration_%s"
    )
    token_form = forms.TokenForm(
        request.user, request.POST if action == "token" else None, auto_id="id_token_%s"
    )
    raw = None
    message = ""
    if request.method == "POST":
        if not take(request, "integration-management", str(request.user.pk), limit=30):
            return throttled()
        if action in {"client", "token", "rotate"} and not request.user.check_password(
            request.POST.get("password", "")
        ):
            message = "Lokales Passwort nicht bestätigt."
        else:
            try:
                if action == "client" and client_form.is_valid():
                    d = client_form.cleaned_data
                    services.create_client(
                        request.user, d["name"], d["capabilities"], d["scope_kind"], d["scope_id"]
                    )
                    return redirect("integrations_manage")
                if action == "token" and token_form.is_valid():
                    d = token_form.cleaned_data
                    _, raw = services.issue(
                        request.user, d["client"].pk, days=d["days"], read_only=d["read_only"]
                    )
                if action == "rotate":
                    _, raw = services.rotate(request.user, request.POST.get("token_id"))
                if action == "revoke":
                    services.revoke(request.user, request.POST.get("token_id"))
                    return redirect("integrations_manage")
                if action == "retire":
                    services.retire(request.user, request.POST.get("client_id"))
                    return redirect("integrations_manage")
            except ValidationError as exc:
                message = " ".join(exc.messages)
    response = render(
        request,
        "integrations/manage.html",
        dict(
            client_form=client_form,
            token_form=token_form,
            raw=raw,
            message=message,
            clients=IntegrationClient.objects.filter(owner=request.user).order_by("-created_at"),
            tokens=Paginator(
                IntegrationToken.objects.filter(client__owner=request.user)
                .select_related("client")
                .order_by("-created_at"),
                30,
            ).get_page(request.GET.get("page")),
        ),
    )
    response["Referrer-Policy"] = "no-referrer"
    return response
