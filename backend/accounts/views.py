from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import forms, services
from .authorization import Scope, allowed, require
from .models import Grant, Group, Membership, User
from .ratelimit import take


def page(request, title, form=None, **context):
    return render(request, "accounts/page.html", {"title": title, "form": form, **context})


def error(form, exc):
    form.add_error(None, exc)


def throttled():
    response = HttpResponse(
        "Zu viele Versuche. Bitte versuche es in 15 Minuten erneut.", status=429
    )
    response["Retry-After"] = "900"
    return response


@require_http_methods(["GET", "POST"])
def signup(request):
    if not settings.PRIVACY_NOTICE_TEXT:
        return HttpResponse("Die Registrierung wird vorbereitet.", status=503)
    form = forms.SignupForm(request.POST or None)
    if request.method == "POST":
        if not take(request, "signup", request.POST.get("email", ""), limit=5):
            return throttled()
        if form.is_valid():
            try:
                services.signup(form.cleaned_data["email"], form.cleaned_data["password"], True)
                return page(
                    request,
                    "Prüfe dein E-Mail-Postfach",
                    text=(
                        "Falls die Adresse neu ist, erhältst du einen Bestätigungslink. "
                        "Bei einem bestehenden Konto kannst du einen neuen Link anfordern."
                    ),
                )
            except ValidationError as exc:
                error(form, exc)
    return page(request, "Konto erstellen", form, signup=True)


@require_http_methods(["GET", "POST"])
def sign_in(request):
    form = forms.LoginForm(request, data=request.POST or None)
    if request.method == "POST":
        if not take(request, "login", request.POST.get("username", "")):
            return throttled()
        if form.is_valid():
            login(request, form.get_user())
            return redirect("account")
    return page(request, "Anmelden", form, login=True, oidc_enabled=settings.OIDC_ENABLED)


@require_POST
def sign_out(request):
    logout(request)
    return redirect("home")


@require_http_methods(["GET", "POST"])
def token_request(request, purpose):
    if purpose not in {"verify", "reset"}:
        raise Http404
    form = forms.EmailForm(request.POST or None)
    title = "Bestätigungslink anfordern" if purpose == "verify" else "Passwort vergessen"
    if request.method == "POST":
        if not take(request, purpose, request.POST.get("email", ""), limit=5):
            return throttled()
        if form.is_valid():
            services.request_token(form.cleaned_data["email"], purpose)
            return page(
                request,
                "Prüfe dein E-Mail-Postfach",
                text=(
                    "Falls ein passendes aktives Konto besteht, erhältst du einen Link per E-Mail."
                ),
            )
    return page(request, title, form)


@require_http_methods(["GET", "POST"])
def token_consume(request, raw, purpose):
    form = forms.ResetForm(request.POST or None) if purpose == "reset" else None
    if request.method == "POST":
        if not take(request, "consume-token"):
            return throttled()
        if form is None or form.is_valid():
            try:
                services.consume_token(
                    raw, purpose, form.cleaned_data["password"] if form else None
                )
                messages.success(
                    request, "E-Mail bestätigt." if purpose == "verify" else "Passwort geändert."
                )
                return redirect("login")
            except ValidationError as exc:
                if form is None:
                    return page(request, "Link ungültig", text=" ".join(exc.messages))
                error(form, exc)
    return page(
        request,
        "E-Mail bestätigen" if purpose == "verify" else "Neues Passwort",
        form,
        confirm=purpose == "verify",
    )


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    form = forms.ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        services.save_profile(request.user, form.cleaned_data)
        messages.success(request, "Profil gespeichert.")
        return redirect("account")
    return page(
        request,
        "Mein Konto",
        form,
        account=True,
        oidc_enabled=settings.OIDC_ENABLED,
        groups_admin=allowed(request.user, "permissions.manage"),
    )


@require_http_methods(["GET"])
def privacy(request):
    return page(
        request,
        "Datenschutzhinweise",
        text=settings.PRIVACY_NOTICE_TEXT or "Noch nicht eingerichtet.",
    )


@login_required
@require_http_methods(["GET"])
def groups(request):
    if allowed(request.user, "permissions.manage"):
        visible = Group.objects.filter(archived_at__isnull=True).order_by("name")
    else:
        visible = [
            g
            for g in Group.objects.filter(archived_at__isnull=True).order_by("name")
            if allowed(request.user, "user.manage_groups", Scope("group", g.pk))
        ]
    return render(
        request,
        "accounts/groups.html",
        {"groups": visible, "can_manage": allowed(request.user, "permissions.manage")},
    )


@login_required
@require_http_methods(["GET", "POST"])
def group_edit(request, group_id=None):
    require(request.user, "permissions.manage")
    group = get_object_or_404(Group, pk=group_id, archived_at__isnull=True) if group_id else None
    form = forms.GroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        try:
            group = services.save_group(request.user, group_id=group_id, **form.cleaned_data)
            return redirect("group_detail", group_id=group.pk)
        except ValidationError as exc:
            error(form, exc)
    return page(request, "Gruppe bearbeiten" if group else "Gruppe erstellen", form)


@login_required
@require_http_methods(["GET", "POST"])
def group_detail(request, group_id):
    group = get_object_or_404(Group, pk=group_id, archived_at__isnull=True)
    admin = allowed(request.user, "permissions.manage")
    if not admin:
        require(request.user, "user.manage_groups", Scope("group", group.pk))
    grant_form = forms.GrantForm(actor=request.user)
    member_form = forms.MembershipForm()
    if request.method == "POST":
        op = request.POST.get("operation")
        if op == "grant":
            require(request.user, "permissions.manage")
            grant_form = forms.GrantForm(request.POST, actor=request.user)
            if grant_form.is_valid():
                try:
                    services.add_grant(request.user, group.pk, grant_form.cleaned_data)
                    return redirect("group_detail", group_id=group.pk)
                except ValidationError as exc:
                    error(grant_form, exc)
        elif op == "membership":
            member_form = forms.MembershipForm(request.POST)
            if member_form.is_valid():
                user = User.objects.filter(email__iexact=member_form.cleaned_data["email"]).first()
                if user is None:
                    member_form.add_error("email", "Kein zuweisbares Konto gefunden.")
                else:
                    try:
                        services.change_membership(
                            request.user,
                            group.pk,
                            user.pk,
                            remove=member_form.cleaned_data["remove"],
                        )
                        return redirect("group_detail", group_id=group.pk)
                    except ValidationError as exc:
                        error(member_form, exc)
        else:
            return HttpResponse(status=400)
    # A delegated membership manager sees no address/phone and only this group's memberships.
    members = Membership.objects.filter(group=group, removed_at__isnull=True).select_related("user")
    return render(
        request,
        "accounts/group.html",
        {
            "group": group,
            "grants": Grant.objects.filter(group=group),
            "members": members,
            "grant_form": grant_form,
            "member_form": member_form,
            "can_manage": admin,
        },
    )


@login_required
@require_POST
def group_archive(request, group_id):
    services.archive_group(request.user, group_id)
    return redirect("groups")


@login_required
@require_POST
def grant_remove(request, group_id, grant_id):
    services.remove_grant(request.user, group_id, grant_id)
    return redirect("group_detail", group_id=group_id)


@login_required
@require_http_methods(["GET", "POST"])
def suspension(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if not allowed(request.user, "admin.manage"):
        require(request.user, "account.suspend", Scope("user", user.pk))
    form = forms.SuspensionForm(request.POST or None, initial={"suspended": not user.is_active})
    if request.method == "POST" and form.is_valid():
        try:
            services.suspend_account(request.user, user.pk, **form.cleaned_data)
            return redirect("groups")
        except ValidationError as exc:
            error(form, exc)
    return page(request, "Kontosperre verwalten", form)


@login_required
@require_http_methods(["GET", "POST"])
def password_change(request):
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm

    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST":
        if not take(request, "password-change", str(request.user.pk), limit=5):
            return throttled()
        if form.is_valid():
            try:
                user = services.change_password(
                    request.user,
                    form.cleaned_data["old_password"],
                    form.cleaned_data["new_password1"],
                )
                update_session_auth_hash(request, user)
                messages.success(
                    request, "Passwort geändert. Andere Sitzungen müssen sich erneut anmelden."
                )
                return redirect("account")
            except ValidationError as exc:
                error(form, exc)
    return page(request, "Passwort ändern", form)


@login_required
@require_http_methods(["GET", "POST"])
def oidc_unlink(request):
    from django.contrib.auth import update_session_auth_hash

    form = forms.ReauthenticateForm(request.POST or None)
    if request.method == "POST":
        if not take(request, "oidc-unlink", str(request.user.pk), limit=5):
            return throttled()
        if form.is_valid():
            try:
                user = services.unlink_oidc(request.user, form.cleaned_data["password"])
                update_session_auth_hash(request, user)
                messages.success(request, "Authentik-Verknüpfung entfernt.")
                return redirect("account")
            except ValidationError as exc:
                error(form, exc)
    return page(
        request,
        "Authentik-Verknüpfung entfernen",
        form,
        text="Eine lokale Anmeldung muss weiter möglich bleiben.",
    )
