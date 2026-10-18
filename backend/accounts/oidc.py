"""Fixed-endpoint Authentik code flow. No identity/email/privilege claim imports."""

import base64
import hashlib
import json
import secrets
import time
from datetime import UTC, datetime
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_http_methods

from .authorization import authorization_write, bump
from .forms import ReauthenticateForm
from .models import OIDCIdentity, OIDCStateUse, User
from .ratelimit import take
from .services import audit
from .views import page, throttled


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(url, data=None, headers=None):
    # All endpoints come from operator configuration, never discovery or token jku/x5u.
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.fragment:
        raise ValueError("HTTPS endpoint required")
    request = Request(url, data=data, headers=headers or {})
    with build_opener(NoRedirect()).open(request, timeout=5) as response:
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Oversized provider response")
        return json.loads(raw)


def callback_url():
    return settings.PUBLIC_BASE_URL + "/konto/oidc/callback/"


def start(request, *, linking=False):
    if not settings.OIDC_ENABLED:
        raise Http404
    request.session.cycle_key()
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    request.session["oidc_flow"] = {
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
        "created": time.time(),
        "link_user": str(request.user.pk) if linking else "",
    }
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    params = dict(
        response_type="code",
        client_id=settings.OIDC_CLIENT_ID,
        redirect_uri=callback_url(),
        scope="openid",
        state=state,
        nonce=nonce,
        code_challenge=challenge,
        code_challenge_method="S256",
    )
    if linking:
        params["prompt"] = "login"
    return redirect(settings.OIDC_AUTHORIZATION_ENDPOINT + "?" + urlencode(params))


@require_http_methods(["POST"])
def sign_in(request):
    if not take(request, "oidc-start"):
        return throttled()
    return start(request)


@login_required
@require_http_methods(["GET", "POST"])
def link(request):
    if (
        not settings.OIDC_ENABLED
        or not request.user.is_employee
        or not request.user.email_verified_at
    ):
        raise PermissionDenied
    form = ReauthenticateForm(request.POST or None)
    if request.method == "POST":
        if not take(request, "oidc-link", str(request.user.pk), limit=5):
            return throttled()
        if form.is_valid():
            if request.user.check_password(form.cleaned_data["password"]):
                return start(request, linking=True)
            form.add_error("password", "Passwort nicht bestätigt.")
    return page(request, "Authentik verbinden", form)


def validate_id_token(encoded, nonce):
    if not isinstance(encoded, str) or len(encoded) > 32768:
        raise ValueError("Oversized ID token")
    header = jwt.get_unverified_header(encoded)
    if header.get("crit"):
        raise ValueError("Unsupported critical JOSE extensions")
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise ValueError("Unsupported signing key")
    keys = fetch_json(settings.OIDC_JWKS_ENDPOINT)["keys"]
    matches = [
        k
        for k in keys
        if k.get("kid") == header["kid"]
        and k.get("kty") == "RSA"
        and k.get("use", "sig") == "sig"
        and k.get("alg", "RS256") == "RS256"
    ]
    if len(matches) != 1:
        raise ValueError("Ambiguous key")
    key = jwt.PyJWK.from_dict(matches[0], algorithm="RS256")
    claims = jwt.decode(
        encoded,
        key.key,
        algorithms=["RS256"],
        audience=settings.OIDC_CLIENT_ID,
        issuer=settings.OIDC_ISSUER,
        options={"require": ["iss", "sub", "aud", "exp", "iat", "nonce"]},
    )
    if not isinstance(claims["sub"], str) or not 0 < len(claims["sub"]) <= 255:
        raise ValueError("Invalid subject")
    if not isinstance(claims["nonce"], str) or not secrets.compare_digest(claims["nonce"], nonce):
        raise ValueError("Invalid nonce")
    if (
        isinstance(claims["aud"], list) and len(claims["aud"]) > 1 or "azp" in claims
    ) and claims.get("azp") != settings.OIDC_CLIENT_ID:
        raise ValueError("Invalid authorized party")
    return claims


def claim_flow(flow):
    """One-time state even when two callbacks load the same session concurrently."""
    try:
        with transaction.atomic():
            OIDCStateUse.objects.create(
                digest=hashlib.sha256(flow["state"].encode()).hexdigest(),
                expires_at=datetime.fromtimestamp(flow["created"] + 300, UTC),
            )
        return True
    except IntegrityError:
        return False


@require_GET
def callback(request):
    if not settings.OIDC_ENABLED:
        raise Http404
    flow = request.session.pop("oidc_flow", None)
    # Persist consumption before processing: a callback URL cannot be replayed later.
    request.session.save()
    if not flow or not secrets.compare_digest(flow["state"], request.GET.get("state", "")):
        return HttpResponse("Anmeldung konnte nicht bestätigt werden.", status=400)
    if not 0 <= time.time() - flow["created"] <= 300 or not request.GET.get("code"):
        return HttpResponse("Anmeldung ist abgelaufen oder wurde abgebrochen.", status=400)
    if len(request.GET["code"]) > 4096 or not claim_flow(flow):
        return HttpResponse("Anmeldung konnte nicht bestätigt werden.", status=400)
    try:
        client_id = quote(settings.OIDC_CLIENT_ID, safe="")
        client_secret = quote(settings.OIDC_CLIENT_SECRET, safe="")
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        response = fetch_json(
            settings.OIDC_TOKEN_ENDPOINT,
            urlencode(
                {
                    "grant_type": "authorization_code",
                    "code": request.GET["code"],
                    "redirect_uri": callback_url(),
                    "code_verifier": flow["verifier"],
                }
            ).encode(),
            {
                "Authorization": "Basic " + basic,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        claims = validate_id_token(response["id_token"], flow["nonce"])
        with authorization_write() as revision:
            identity = OIDCIdentity.objects.filter(
                issuer=settings.OIDC_ISSUER, subject=claims["sub"]
            ).first()
            if flow["link_user"]:
                if not request.user.is_authenticated or str(request.user.pk) != flow["link_user"]:
                    raise PermissionDenied
                user = User.objects.get(
                    pk=request.user.pk,
                    is_active=True,
                    is_employee=True,
                    email_verified_at__isnull=False,
                )
                if identity and identity.user_id != user.pk:
                    raise PermissionDenied
                current = OIDCIdentity.objects.filter(user=user).first()
                if current and (
                    current.issuer != settings.OIDC_ISSUER or current.subject != claims["sub"]
                ):
                    raise PermissionDenied
                if not identity:
                    OIDCIdentity.objects.create(
                        user=user, issuer=settings.OIDC_ISSUER, subject=claims["sub"]
                    )
                    audit(user, "oidc.linked", subject=user)
                    bump(revision)
            else:
                if not identity:
                    raise PermissionDenied
                user = User.objects.get(
                    pk=identity.user_id,
                    is_active=True,
                    is_employee=True,
                    email_verified_at__isnull=False,
                )
            login(request, user, backend="accounts.backends.EmailBackend")
            audit(user, "oidc.login", subject=user)
        messages.success(request, "Mit Authentik angemeldet.")
        from accounts.navigation import operational_user

        return redirect("inventory_dashboard" if operational_user(user) else "account")
    except Exception:
        # Provider errors may embed tokens; never log exception bodies.
        return page(
            request,
            "Authentik-Anmeldung nicht möglich",
            text=("Bitte verwende die lokale Anmeldung oder lasse die Kontoverknüpfung prüfen."),
        )
