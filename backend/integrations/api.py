"""Small versioned adapters. No independent allocation or custody state machine."""

import logging
import re

from accounts.authorization import authorization_write
from accounts.limits import limited
from accounts.ratelimit import take
from bookings import services as bookings
from bookings.models import BookingPolicy
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from inventory import csvio
from inventory import services as inventory
from inventory.models import Asset, ImportPreview
from lending import services as lending
from lending.models import Operation
from resources import services as resources

from . import dto, services
from . import transport as t
from .models import APIImport

PERIOD_FIELDS = ["start", "end", "pickup_at", "return_at", "unit_id", "pool_id", "optional_ids"]
ROUTES = [
    ("GET", r"resources/", "catalog.read", False, "resources"),
    ("GET", r"assets/", "inventory.read", False, "assets"),
    ("GET", r"assets/export.csv", "inventory.export", False, "export"),
    ("POST", r"assets/imports/", "inventory.import", True, "import_create"),
    ("GET", r"assets/imports/(?P<id>[0-9a-f-]{36})/", "inventory.import", False, "import_read"),
    (
        "POST",
        r"assets/imports/(?P<id>[0-9a-f-]{36})/commit/",
        "inventory.import",
        True,
        "import_commit",
    ),
    ("GET", r"assets/(?P<id>[0-9a-f-]{36})/", "inventory.read", False, "asset"),
    ("POST", r"assets/(?P<id>[0-9a-f-]{36})/move/", "inventory.move", True, "move"),
    ("POST", r"identifiers/resolve/", "identifiers.resolve", False, "resolve"),
    ("POST", r"availability/", "availability.read", False, "availability"),
    ("GET", r"bookings/", "bookings.read", False, "bookings"),
    ("POST", r"bookings/", "bookings.create", True, "confirm"),
    ("GET", r"bookings/(?P<id>[0-9a-f-]{36})/", "bookings.read", False, "booking"),
    ("POST", r"bookings/(?P<id>[0-9a-f-]{36})/cancel/", "bookings.cancel", True, "cancel"),
    ("GET", r"loans/", "loans.read", False, "loans"),
    ("GET", r"loans/(?P<id>[0-9a-f-]{36})/", "loans.read", False, "loan"),
    ("POST", r"loans/checkout/", "loans.checkout", True, "checkout"),
    ("POST", r"loans/(?P<id>[0-9a-f-]{36})/return/", "loans.return", True, "return"),
]


def asset_rows(actor, request):
    t.filters(
        request, {"page", "page_size", "q", "location_id", "category_id", "condition", "lifecycle"}
    )
    qs = inventory.visible_assets(actor).filter(archived_at__isnull=True).order_by("id")
    for field in ["location_id", "category_id"]:
        if request.GET.get(field):
            qs = qs.filter(**{field: t.uid(request.GET[field])})
    if request.GET.get("q"):
        from django.db.models import Q

        q = request.GET["q"]
        qs = qs.filter(Q(name__icontains=q) | Q(inventory_number__icontains=q))
    for field, values in [
        ("condition", Asset.Condition.values),
        ("lifecycle", Asset.Lifecycle.values),
    ]:
        if request.GET.get(field):
            if request.GET[field] not in values:
                raise t.APIError(400, "invalid_filter")
            qs = qs.filter(**{field: request.GET[field]})
    return qs


def read_import(actor, client, pk):
    link = APIImport.objects.select_related("preview").get(client=client, preview_id=pk)
    row = ImportPreview.objects.get(pk=link.preview_id, actor=actor)
    if row.committed_at:
        for pk in row.created_asset_ids:
            inventory.read_asset(actor, pk)
    else:
        for item in row.rows:
            csvio.validate_row(actor, item)
    return row


def import_dto(row):
    return dict(
        id=str(row.pk),
        expires_at=t.iso(row.expires_at),
        committed_at=t.iso(row.committed_at),
        row_count=len(row.rows),
        created_asset_ids=row.created_asset_ids,
    )


def dispatch(name, request, actor, client, ceiling, params):
    pk = params.get("id")
    if name == "resources":
        t.filters(request, {"page", "page_size", "q"})
        rows = resources.visible_resources(actor).filter(archived_at=None).order_by("id")
        if request.GET.get("q"):
            rows = rows.filter(title__icontains=request.GET["q"])
        result = [
            dto.resource(r, ceiling)
            for r in rows
            if ceiling.includes(resources.resource_scope(r))
            and BookingPolicy.objects.filter(resource=r).exists()
        ]
        return t.paginate(request, result)
    if name in {"assets", "export"}:
        rows = asset_rows(actor, request)
        if name == "export":
            if rows.count() > 1000:
                raise t.APIError(
                    422, "export_too_large", "Export enger filtern; maximal 1000 Assets."
                )
            from django.http import HttpResponse

            response = HttpResponse(
                csvio.export_csv(actor, rows), content_type="text/csv; charset=utf-8"
            )
            response["Content-Disposition"] = 'attachment; filename="deelvo-api-inventory.csv"'
            return response
        return t.paginate(request, [dto.asset(a, ceiling) for a in rows])
    if name in {"asset", "move"}:
        row = inventory.read_asset(actor, pk)
        if name == "move":
            data = t.body(request, {"location_id", "reason"})
            revision = t.revision(request, "asset", row)
            row = inventory.move_asset(
                actor, row.pk, t.uid(data.get("location_id")), t.text(data, "reason"), revision
            )
        response = JsonResponse(dto.asset(row, ceiling))
        response["ETag"] = t.etag("asset", row)
        return response
    if name == "resolve":
        data = t.body(request, {"namespace_id", "code"})
        result = inventory.resolve_identifier(
            actor, t.uid(data.get("namespace_id")), t.text(data, "code", maximum=256)
        )
        return dict(
            status=result.status,
            asset_id=str(result.asset_id) if result.asset_id else None,
            unit_id=str(result.unit_id) if result.unit_id else None,
            resource_id=str(result.resource_id) if result.resource_id else None,
        )
    if name == "import_create":
        import csv
        import io

        data = t.body(request, {"csv"})
        text = t.text(data, "csv", maximum=60000)
        columns = csv.DictReader(io.StringIO(text)).fieldnames or []
        if set(columns) - set(csvio.CORE_FIELDS):
            raise t.APIError(400, "invalid_columns", "Nur dokumentierte Basisfelder importieren.")
        row = csvio.preview_import(actor, SimpleUploadedFile("integration.csv", text.encode()))
        APIImport.objects.create(client=client, preview=row)
        return JsonResponse(import_dto(row), status=201)
    if name in {"import_read", "import_commit"}:
        row = read_import(actor, client, pk)
        if name == "import_commit":
            t.body(request, set())
            csvio.commit_import(actor, row.pk)
            row.refresh_from_db()
        return import_dto(row)
    if name in {"availability", "confirm"}:
        data = t.body(request, {"resource_id", *PERIOD_FIELDS})
        resource = resources.visible_resources(actor).get(pk=t.uid(data.get("resource_id")))
        dto.check(ceiling, resources.resource_scope(resource))
        policy = BookingPolicy.objects.get(resource=resource)
        values = t.periods(policy, data)
        start, end = values.pop("start"), values.pop("end")
        if name == "availability":
            result = bookings.availability(actor, resource.pk, start, end, **values)
            return dict(
                code=result.code,
                unit_id=str(result.unit_id) if result.unit_id else None,
                policy_revision=result.policy_revision,
            )
        row = bookings.confirm(actor, resource.pk, start, end, t.key(request, client), **values)
        response = JsonResponse(
            dto.booking(bookings.read_booking(actor, row.pk), ceiling), status=201
        )
        response["ETag"] = t.etag("booking", row)
        return response
    if name == "bookings":
        t.filters(request, {"page", "page_size", "view", "resource_id"})
        if request.GET.get("view", "own") not in {"own", "operations"}:
            raise t.APIError(400, "invalid_filter")
        rows = bookings.visible_bookings(
            actor, operational=request.GET.get("view") == "operations"
        ).order_by("id")
        if request.GET.get("resource_id"):
            rows = rows.filter(resource_id=t.uid(request.GET["resource_id"]))
        return t.paginate(
            request,
            [
                dto.booking(row, ceiling)
                for row in rows
                if ceiling.includes(resources.resource_scope(row.resource))
            ],
        )
    if name in {"booking", "cancel"}:
        row = bookings.read_booking(actor, pk)
        dto.check(ceiling, resources.resource_scope(row.resource))
        if name == "cancel":
            data = t.body(request, {"reason"})
            row = bookings.cancel(
                actor, row.pk, t.revision(request, "booking", row), t.text(data, "reason")
            )
        response = JsonResponse(dto.booking(row, ceiling))
        response["ETag"] = t.etag("booking", row)
        return response
    if name == "loans":
        t.filters(request, {"page", "page_size", "view"})
        if request.GET.get("view", "own") not in {"own", "operations"}:
            raise t.APIError(400, "invalid_filter")
        rows = lending.visible_loans(
            actor, operational=request.GET.get("view") == "operations"
        ).order_by("id")
        result = []
        for row in rows:
            if all(
                ceiling.includes(resources.resource_scope(line.booking.resource))
                for line in row.lines.all()
            ):
                result.append(dto.loan(actor, row.pk, ceiling))
        return t.paginate(request, result)
    if name == "loan":
        t.filters(request, set())
        return dto.loan(actor, pk, ceiling)
    if name == "checkout":
        data = t.body(request, {"borrower_id", "bookings"})
        entries = data.get("bookings")
        if not isinstance(entries, list) or not 1 <= len(entries) <= 50:
            raise t.APIError(400, "invalid_fields")
        checks = {}
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - {
                "booking_id",
                "condition",
                "accessories_checked",
                "accessories",
            }:
                raise t.APIError(400, "invalid_fields")
            bid = str(t.uid(entry.get("booking_id")))
            if bid in checks or type(entry.get("accessories_checked")) is not bool:
                raise t.APIError(400, "invalid_fields")
            checks[bid] = dict(
                condition=t.text(entry, "condition", maximum=20),
                accessories_checked=entry["accessories_checked"],
                accessories=t.text(entry, "accessories", maximum=2000, required=False) or "",
            )
        row = lending.checkout(
            actor,
            t.uid(data.get("borrower_id")),
            list(checks),
            t.key(request, client),
            checks=checks,
        )
        return JsonResponse(dto.loan(actor, row.pk, ceiling), status=201)
    if name == "return":
        dto.loan(actor, pk, ceiling)
        data = t.body(request, {"lines"})
        entries = data.get("lines")
        if not isinstance(entries, list) or not 1 <= len(entries) <= 50:
            raise t.APIError(400, "invalid_fields")
        selections = {}
        key = t.key(request, client)
        prior = Operation.objects.filter(actor=actor, kind="return", key=key).exists()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - {
                "line_id",
                "revision",
                "condition",
                "accessories_checked",
                "note",
            }:
                raise t.APIError(400, "invalid_fields")
            line_id = str(t.uid(entry.get("line_id")))
            if line_id in selections or type(entry.get("accessories_checked")) is not bool:
                raise t.APIError(400, "invalid_fields")
            revision = t.number(entry.get("revision"), minimum=1)
            from lending.models import LoanLine

            line = LoanLine.objects.get(pk=line_id, loan_id=pk)
            if not prior and line.revision != revision:
                raise t.APIError(409, "revision_conflict")
            selections[line_id] = dict(
                revision=revision,
                condition=t.text(entry, "condition", maximum=20),
                accessories_checked=entry["accessories_checked"],
                note=t.text(entry, "note", maximum=2000, required=False) or "",
            )
        row = lending.return_lines(actor, pk, selections, key)
        return dto.loan(actor, row.pk, ceiling)
    raise t.APIError(404, "not_found")


@csrf_exempt
def endpoint(request, endpoint=""):
    try:
        matches = [
            (method, cap, write, name, m.groupdict())
            for method, pattern, cap, write, name in ROUTES
            if (m := re.fullmatch(pattern, endpoint))
        ]
        if not matches:
            raise t.APIError(404, "not_found")
        match = next((row for row in matches if row[0] == request.method), None)
        if not match:
            raise t.APIError(405, "method_not_allowed")
        _method, cap, write, name, params = match
        header = request.headers.get("Authorization", "")
        try:
            token, _ = services.authenticate(header)
        except (PermissionDenied, ObjectDoesNotExist):
            if not take(request, "api-invalid-auth", limit=60):
                raise t.APIError(429, "rate_limited") from None
            raise t.APIError(401, "invalid_token") from None
        if not take(
            request,
            "api-write" if write else "api-read",
            str(token.client_id),
            limit=120 if write else 600,
        ):
            raise t.APIError(429, "rate_limited")
        with authorization_write():
            try:
                token, ceiling = services.authenticate(header)
            except (PermissionDenied, ObjectDoesNotExist):
                raise t.APIError(401, "invalid_token") from None
            if cap not in ceiling.capabilities:
                raise t.APIError(403, "capability_denied")
            if name not in {"resources", "assets", "export", "bookings", "loans"}:
                t.filters(request, set())
            with limited(ceiling):
                response = dispatch(
                    name, request, token.client.owner, token.client, ceiling, params
                )
                if not hasattr(response, "status_code"):
                    response = JsonResponse(response)
    except t.APIError as exc:
        response = error(request, exc.status, exc.code, exc.message)
    except (PermissionDenied, ObjectDoesNotExist):
        response = error(request, 404, "not_found", "Objekt nicht verfügbar.")
    except ValidationError:
        response = error(
            request, 422, "domain_validation", "Fachliche Voraussetzung oder Verfügbarkeit prüfen."
        )
    except IntegrityError:
        response = error(request, 409, "conflict", "Aktuellen Stand neu prüfen.")
    except (ValueError, TypeError, KeyError, OverflowError):
        response = error(request, 400, "invalid_fields", "Eingaben prüfen.")
    except Exception:
        logging.getLogger("deelvo.api").error("api_internal_error")
        response = error(
            request,
            500,
            "internal_error",
            "Anfrage nicht verarbeitet; Request-ID zur Klärung verwenden.",
        )
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def error(request, status, code, message):
    response = JsonResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request, "request_id", ""),
            }
        },
        status=status,
    )
    if status == 401:
        response["WWW-Authenticate"] = 'Bearer realm="Deelvo API", error="invalid_token"'
    if status == 429:
        response["Retry-After"] = "900"
    if status == 405:
        response["Allow"] = "GET, POST"
    return response
