"""Session-bound staffed context with a database-serialized reset boundary."""

import secrets

from accounts.authorization import authorization_write
from accounts.navigation import operational_user
from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

from .models import StaffedContext


def reset(request, mode="lookup"):
    with authorization_write():
        request.session.pop("lending_cart", None)
        prior = request.session.get("staffed_terminal")
        row = (
            StaffedContext.objects.filter(pk=prior["id"], owner=request.user).first()
            if prior
            else None
        )
        if row:
            row.generation = secrets.token_hex(16)
            row.touched_at = timezone.now()
            row.save()
        else:
            row = StaffedContext.objects.create(
                owner=request.user, generation=secrets.token_hex(16), touched_at=timezone.now()
            )
        request.session["staffed_terminal"] = {
            "id": str(row.pk),
            "generation": row.generation,
            "mode": mode,
        }


def rotate(request):
    """Changing a beneficiary/finished operation invalidates previously rendered forms."""
    prior = request.session.get("staffed_terminal")
    if prior:
        row = StaffedContext.objects.get(pk=prior["id"], owner=request.user)
        row.generation = secrets.token_hex(16)
        row.save(update_fields=["generation"])
        prior["generation"] = row.generation
        request.session["staffed_terminal"] = prior


def context(request):
    return {
        "terminal": request.session.get("staffed_terminal"),
        "terminal_idle_seconds": settings.TERMINAL_IDLE_SECONDS,
    }


class TerminalGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        terminal = request.session.get("staffed_terminal")
        if not terminal:
            return self.get_response(request)
        # The common lock spans validation, domain action and generation rotation.
        # Concurrent mode/reset/person changes cannot authorize a stale confirmation.
        with authorization_write():
            row = StaffedContext.objects.select_for_update().filter(pk=terminal["id"]).first()
            now = timezone.now()
            if (
                not request.user.is_authenticated
                or not row
                or row.owner_id != request.user.pk
                or row.revoked
                or (now - row.touched_at).total_seconds() > settings.TERMINAL_IDLE_SECONDS
            ):
                if row:
                    row.revoked = True
                    row.save(update_fields=["revoked"])
                logout(request)
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"error": "terminal_locked"}, status=401)
                return redirect("login")
            if (
                request.method == "POST"
                and request.path.startswith(("/betrieb/", "/ausleihen/"))
                and request.POST.get("terminal_generation") != row.generation
            ):
                return JsonResponse({"error": "terminal_context_changed"}, status=409)
            if terminal["generation"] != row.generation:
                request.session.pop("lending_cart", None)
                terminal["generation"] = row.generation
                terminal["mode"] = "lookup"
                request.session["staffed_terminal"] = terminal
                return redirect("staffed_terminal")
            row.touched_at = now
            row.save(update_fields=["touched_at"])
            response = self.get_response(request)
            # Persist changed terminal/cart session while still inside the serial boundary.
            if (
                request.session.session_key
                and request.session.modified
                and not request.session.is_empty()
            ):
                request.session.save()
            return response


def require_staff(request):
    from django.core.exceptions import PermissionDenied

    if not operational_user(request.user):
        raise PermissionDenied
