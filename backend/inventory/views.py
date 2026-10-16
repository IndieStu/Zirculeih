from functools import wraps
from typing import Any

from accounts.authorization import allowed, require
from accounts.models import AuditEvent, Grant, User
from accounts.ratelimit import take
from accounts.views import throttled
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import csvio, extensions, forms, services
from .models import (
    Asset,
    AssetMedia,
    Category,
    CustomFieldDefinition,
    Identifier,
    IdentifierNamespace,
    ImportPreview,
    Location,
)


def inventory_page(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (
            Asset.DoesNotExist,
            AssetMedia.DoesNotExist,
            Identifier.DoesNotExist,
            IdentifierNamespace.DoesNotExist,
            ImportPreview.DoesNotExist,
            CustomFieldDefinition.DoesNotExist,
            Location.DoesNotExist,
            Category.DoesNotExist,
            PermissionDenied,
            FileNotFoundError,
        ) as exc:
            # No distinction between absent and unauthorized objects on inventory URLs.
            raise Http404 from exc

    return wrapped


def any_action(actor, action):
    if not User.objects.filter(
        pk=actor.pk, is_active=True, email_verified_at__isnull=False
    ).exists():
        return False
    if not Grant.objects.filter(
        action=action,
        effect="allow",
        group__is_active=True,
        group__archived_at__isnull=True,
        group__membership__user=actor,
        group__membership__removed_at__isnull=True,
    ).exists():
        return False
    if allowed(actor, action):
        return True
    if action.startswith(("resource.", "identifier.", "booking.", "loan.", "agreement.")):
        from resources.models import Resource
        from resources.services import resource_scope

        if any(allowed(actor, action, resource_scope(r)) for r in Resource.objects.all()):
            return True
    return any(
        allowed(actor, action, services.tree_scope(n))
        for model in (Location, Category)
        for n in model.objects.all()
    ) or any(
        allowed(actor, action, services.asset_scope(a))
        for a in Asset.objects.select_related("location", "category")
    )


def navigation(actor):
    return {
        "can_create": any_action(actor, "asset.manage") and any_action(actor, "asset.read"),
        "can_lookup": any_action(actor, "identifier.resolve"),
        "can_locations": any_action(actor, "location.read") or any_action(actor, "location.manage"),
        "can_categories": any_action(actor, "category.read")
        or any_action(actor, "category.manage"),
        "can_import": any_action(actor, "asset.import"),
        "can_export": any_action(actor, "asset.export"),
        "can_namespaces": allowed(actor, "identifier.namespace_manage"),
        "can_fields": allowed(actor, "custom_field.manage"),
        "can_tags": allowed(actor, "category.manage"),
    }


@inventory_page
@require_http_methods(["GET"])
def dashboard(request):
    nav = navigation(request.user)
    assets = services.visible_assets(request.user)
    booking_can_operate = any(
        any_action(request.user, action)
        for action in ("booking.read_all", "booking.configure", "booking.block")
    )
    loan_can_operate = any(
        any_action(request.user, action) for action in ("loan.read", "loan.checkout", "loan.return")
    )
    if (
        not any(nav.values())
        and not assets.exists()
        and not booking_can_operate
        and not loan_can_operate
    ):
        return redirect("account")
    from datetime import datetime, time, timedelta

    from bookings.models import BookingIncident
    from bookings.services import visible_bookings
    from django.utils import timezone

    bookings = visible_bookings(request.user, operational=True) if booking_can_operate else None
    today_start = datetime.combine(
        timezone.localdate(), time.min, tzinfo=timezone.get_current_timezone()
    )
    today = (
        bookings.filter(start__lt=today_start + timedelta(days=1), end__gt=today_start).exclude(
            status="cancelled"
        )
        if bookings is not None
        else []
    )
    incidents = (
        BookingIncident.objects.filter(booking__in=bookings, is_open=True)
        if bookings is not None
        else BookingIncident.objects.none()
    )
    from lending.models import LoanLine
    from lending.services import pickup_bookings, visible_loans

    loan_rows = visible_loans(request.user, operational=True) if loan_can_operate else None
    loan_lines = (
        LoanLine.objects.filter(loan__in=loan_rows, returned_at__isnull=True).select_related(
            "booking__resource"
        )
        if loan_rows is not None
        else LoanLine.objects.none()
    )
    overdue_lines = loan_lines.filter(expected_return__lt=timezone.now())
    pickups = (
        pickup_bookings(request.user).filter(
            appointment__pickup_at__gte=today_start,
            appointment__pickup_at__lt=today_start + timedelta(days=1),
        )
        if loan_can_operate
        else []
    )
    returns_today = loan_lines.filter(
        expected_return__gte=today_start, expected_return__lt=today_start + timedelta(days=1)
    )
    attention = assets.filter(
        Q(condition__in=["damaged", "inspection"])
        | Q(lifecycle__in=["unavailable", "maintenance", "lost"])
    ).filter(archived_at__isnull=True)
    inactive_locations = [
        n
        for n in Location.objects.filter(is_active=False)
        if allowed(request.user, "location.read", services.tree_scope(n))
    ]
    return render(
        request,
        "inventory/dashboard.html",
        {
            **nav,
            "attention": attention[:20],
            "attention_count": attention.count(),
            "inactive_locations": inactive_locations[:10],
            "asset_count": assets.count(),
            "archived_count": assets.filter(archived_at__isnull=False).count(),
            "booking_can_operate": booking_can_operate,
            "loan_can_operate": loan_can_operate,
            "overdue_lines": overdue_lines[:20],
            "overdue_count": overdue_lines.count(),
            "today_pickups": pickups[:20],
            "today_returns": returns_today[:20],
            "today_bookings": today[:20],
            "booking_incident_count": incidents.count(),
        },
    )


def filtered_assets(request):
    qs = services.visible_assets(request.user)
    query = request.GET.get("q", "")[:200].strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(inventory_number__icontains=query)
            | Q(description__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(model__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()
    for field in ("location", "category"):
        if request.GET.get(field):
            try:
                model = Location if field == "location" else Category
                ids = services.descendants(model, model.objects.get(pk=request.GET[field]).pk)
                qs = qs.filter(**{field + "_id__in": ids})
            except (ValueError, ValidationError, model.DoesNotExist):
                qs = qs.none()
    for field in ("condition", "lifecycle"):
        if request.GET.get(field):
            qs = qs.filter(**{field: request.GET[field]})
    if request.GET.get("archived") != "all":
        qs = qs.filter(archived_at__isnull=True)
    return qs


@inventory_page
@require_http_methods(["GET"])
def asset_list(request):
    nav = navigation(request.user)
    if not any_action(request.user, "asset.read"):
        raise PermissionDenied
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "inventory/list.html",
        {
            **nav,
            "page_obj": Paginator(filtered_assets(request), 30).get_page(request.GET.get("page")),
            "pagination_query": query.urlencode() + "&" if query else "",
            "locations": forms.permitted_nodes(request.user, Location, "location.read"),
            "categories": forms.permitted_nodes(request.user, Category, "category.read"),
            "conditions": Asset.Condition.choices,
            "lifecycles": Asset.Lifecycle.choices,
        },
    )


@inventory_page
@require_http_methods(["GET"])
def asset_detail(request, asset_id):
    asset = services.read_asset(request.user, asset_id)
    scope = services.asset_scope(asset)
    sensitive = allowed(request.user, "asset.read_sensitive", scope)
    financial = allowed(request.user, "asset.read_financial", scope)
    media = asset.media.filter(archived_at__isnull=True)
    if not sensitive:
        media = media.filter(is_sensitive=False)
    events = AuditEvent.objects.filter(object_id=str(asset.pk)).order_by("-created_at")[:20]
    labels = {
        "asset.created": "Asset angelegt",
        "asset.updated": "Stammdaten geändert",
        "asset.archived": "Asset archiviert",
        "asset.moved": "Standort geändert",
        "asset.custom_value_updated": "Zusatzfeld geändert",
        "asset.media_uploaded": "Medium hochgeladen",
        "asset.media_archived": "Medium archiviert",
    }
    for event in events:
        event.display_action = labels.get(event.action, "Inventar geändert")
    return render(
        request,
        "inventory/detail.html",
        {
            "asset": asset,
            "sensitive": sensitive,
            "financial": financial,
            "media": media,
            "values": extensions.visible_custom_values(request.user, asset),
            "identifiers": asset.identifiers.select_related("namespace").all(),
            "movements": asset.movements.select_related("actor").order_by("-created_at")[:20],
            "events": events,
            "can_edit": allowed(request.user, "asset.manage", scope),
            "can_move": allowed(request.user, "asset.move", scope),
            "can_archive": allowed(request.user, "asset.archive", scope),
            "can_assign": allowed(request.user, "identifier.assign", scope),
            "can_retire": allowed(request.user, "identifier.retire", scope),
            "can_attach": allowed(request.user, "asset.attach", scope),
        },
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def asset_edit(request, asset_id=None):
    asset = services.read_asset(request.user, asset_id, "asset.manage") if asset_id else None
    if not any_action(request.user, "asset.manage") or not any_action(request.user, "asset.read"):
        raise PermissionDenied
    form = forms.AssetForm(request.user, request.POST or None, instance=asset)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        revision = data.pop("revision")
        try:
            scope_asset = asset or Asset(location=data["location"], category=data["category"])
            require(request.user, "asset.read", services.asset_scope(scope_asset))
            saved = services.save_asset(
                request.user, data, asset_id=asset_id, expected_revision=revision
            )
            messages.success(request, "Inventar gespeichert.")
            return redirect("asset_detail", asset_id=saved.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "inventory/form.html",
        {"title": "Asset bearbeiten" if asset else "Asset anlegen", "form": form},
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def asset_move(request, asset_id):
    asset = services.read_asset(request.user, asset_id, "asset.move")
    form = forms.MoveForm(request.POST or None, initial={"revision": asset.revision})
    form.fields["location"].queryset = forms.permitted_nodes(
        request.user, Location, "location.read"
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.move_asset(
                request.user,
                asset.pk,
                form.cleaned_data["location"].pk,
                form.cleaned_data["reason"],
                form.cleaned_data["revision"],
            )
            return redirect("asset_detail", asset_id=asset.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request, "inventory/form.html", {"title": f"{asset.name}: Standort ändern", "form": form}
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def asset_archive(request, asset_id):
    asset = services.read_asset(request.user, asset_id, "asset.archive")
    form = forms.ReasonForm(request.POST or None, initial={"revision": asset.revision})
    if request.method == "POST" and form.is_valid():
        try:
            services.archive_asset(
                request.user, asset.pk, form.cleaned_data["revision"], form.cleaned_data["reason"]
            )
            return redirect("asset_detail", asset_id=asset.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "inventory/form.html",
        {"title": f"{asset.name}: archivieren und ausmustern", "form": form},
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def lookup(request):
    if not any_action(request.user, "identifier.resolve"):
        raise PermissionDenied
    form = forms.LookupForm(request.POST or None)
    result = None
    if request.method == "POST":
        if not take(request, "identifier-lookup", str(request.user.pk), limit=600):
            return throttled()
        if form.is_valid():
            result = services.resolve_identifier(
                request.user, form.cleaned_data["namespace"].pk, form.cleaned_data["code"]
            )
    can_read_result = False
    can_manage_resource = False
    if result and result.asset_id:
        identified = Asset.objects.get(pk=result.asset_id)
        can_read_result = allowed(request.user, "asset.read", services.asset_scope(identified))
    if result and result.resource_id:
        from resources.models import Resource
        from resources.services import resource_scope

        can_manage_resource = allowed(
            request.user,
            "resource.manage",
            resource_scope(Resource.objects.get(pk=result.resource_id)),
        )
    if result is not None:
        form = forms.LookupForm(initial={"namespace": request.POST.get("namespace")})
    return render(
        request,
        "inventory/lookup.html",
        {
            "form": form,
            "result": result,
            "can_read_result": can_read_result,
            "can_manage_resource": can_manage_resource,
        },
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def identifier_add(request, asset_id):
    asset = services.read_asset(request.user, asset_id, "identifier.assign")
    form = forms.IdentifierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.assign_identifier(
                request.user,
                asset.pk,
                form.cleaned_data["namespace"].pk,
                form.cleaned_data["raw"],
                form.cleaned_data["kind"],
                form.cleaned_data["source"],
            )
            return redirect("asset_detail", asset_id=asset.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "inventory/form.html", {"title": "Identifier zuordnen", "form": form})


@inventory_page
@require_http_methods(["GET", "POST"])
def identifier_retire(request, asset_id, identifier_id):
    asset = services.read_asset(request.user, asset_id, "identifier.retire")
    form = forms.ReasonForm(request.POST or None, initial={"revision": asset.revision})
    if request.method == "POST" and form.is_valid():
        try:
            services.retire_identifier(
                request.user, asset.pk, identifier_id, form.cleaned_data["reason"]
            )
            return redirect("asset_detail", asset_id=asset.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request, "inventory/form.html", {"title": "Identifier dauerhaft stilllegen", "form": form}
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def tree_view(request, kind, node_id=None):
    model, form_type, action = (
        (Location, forms.LocationForm, "location")
        if kind == "locations"
        else (Category, forms.CategoryForm, "category")
    )
    node = get_object_or_404(model, pk=node_id) if node_id else None
    if not any_action(request.user, action + ".read") and not any_action(
        request.user, action + ".manage"
    ):
        raise PermissionDenied
    if node:
        require(request.user, action + ".manage", services.tree_scope(node))
    form = form_type(
        request.POST or None, instance=node, initial={"revision": node.revision if node else 0}
    )
    form.fields["parent"] = forms.NodeChoice(
        label="Übergeordnet",
        required=False,
        queryset=forms.permitted_nodes(request.user, model, action + ".manage").exclude(
            pk=node.pk if node else None
        ),
    )
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        revision = data.pop("revision")
        try:
            services.save_tree(
                request.user, model, data, node_id=node_id, expected_revision=revision
            )
            return redirect("locations" if kind == "locations" else "categories")
        except ValidationError as exc:
            form.add_error(None, exc)
    nodes = [
        n
        for n in model.objects.all()
        if allowed(request.user, action + ".read", services.tree_scope(n))
        or allowed(request.user, action + ".manage", services.tree_scope(n))
    ]
    for entry in nodes:
        entry.can_manage = allowed(request.user, action + ".manage", services.tree_scope(entry))
    return render(
        request,
        "inventory/tree.html",
        {
            "title": "Standorte" if kind == "locations" else "Kategorien",
            "nodes": nodes,
            "form": form,
            "kind": kind,
            "can_manage": any_action(request.user, action + ".manage"),
        },
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def configuration(request, kind):
    action = {
        "namespaces": "identifier.namespace_manage",
        "fields": "custom_field.manage",
        "tags": "category.manage",
    }[kind]
    require(request.user, action)
    form_type: Any = {
        "namespaces": forms.NamespaceForm,
        "fields": forms.FieldDefinitionForm,
        "tags": forms.TagForm,
    }[kind]
    form = form_type(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            data = dict(form.cleaned_data)
            if kind == "namespaces":
                services.save_namespace(request.user, **data)
            elif kind == "fields":
                data["options"] = [
                    s.strip() for s in data.pop("option_lines").splitlines() if s.strip()
                ]
                extensions.create_field(request.user, data)
            else:
                services.add_tag(request.user, **data)
            messages.success(request, "Konfiguration gespeichert.")
            return redirect("inventory_" + kind)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "inventory/form.html",
        {
            "title": {
                "namespaces": "Code-Namensraum anlegen",
                "fields": "Zusatzfeld anlegen",
                "tags": "Schlagwort anlegen",
            }[kind],
            "form": form,
        },
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def custom_value(request, asset_id):
    asset = services.read_asset(request.user, asset_id, "asset.manage")
    form = forms.CustomValueForm(request.POST or None, initial={"revision": asset.revision})
    if not allowed(request.user, "asset.read_sensitive", services.asset_scope(asset)):
        form.fields["definition"].queryset = CustomFieldDefinition.objects.filter(
            is_active=True, is_sensitive=False
        )
    if request.method == "POST" and form.is_valid():
        try:
            extensions.set_custom_value(
                request.user,
                asset.pk,
                form.cleaned_data["definition"].pk,
                form.cleaned_data["value"],
                form.cleaned_data["revision"],
            )
            return redirect("asset_detail", asset_id=asset.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "inventory/form.html", {"title": "Zusatzfeldwert setzen", "form": form})


@inventory_page
@require_http_methods(["GET", "POST"])
def media_upload(request, asset_id):
    asset = services.read_asset(request.user, asset_id, "asset.attach")
    form = forms.UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not take(request, "inventory-upload", str(request.user.pk), limit=20):
            return throttled()
        if form.is_valid():
            try:
                extensions.upload_media(
                    request.user,
                    asset.pk,
                    form.cleaned_data["file"],
                    form.cleaned_data["is_sensitive"],
                )
                return redirect("asset_detail", asset_id=asset.pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(
        request,
        "inventory/form.html",
        {"title": "Bild oder Textdokument hochladen", "form": form, "multipart": True},
    )


@inventory_page
@require_http_methods(["GET"])
def media_download(request, media_id):
    row = extensions.read_media(request.user, media_id)
    response = FileResponse(
        extensions.media_storage().open(row.storage_name, "rb"),
        as_attachment=not row.is_image,
        filename=row.display_name,
        content_type=row.content_type,
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@inventory_page
@require_POST
def media_archive(request, media_id):
    row = extensions.read_media(request.user, media_id)
    extensions.archive_media(request.user, media_id)
    return redirect("asset_detail", asset_id=row.asset_id)


@inventory_page
@require_http_methods(["GET", "POST"])
def csv_import(request):
    if not any_action(request.user, "asset.import"):
        raise PermissionDenied
    form = forms.CSVForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not take(request, "csv-import", str(request.user.pk), limit=10):
            return throttled()
        if form.is_valid():
            try:
                preview = csvio.preview_import(request.user, form.cleaned_data["file"])
                return redirect("csv_preview", preview_id=preview.pk)
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(
        request,
        "inventory/form.html",
        {
            "title": "CSV-Import prüfen",
            "form": form,
            "multipart": True,
            "text": (
                "Erforderliche Spalten: inventory_number, name, location_id, category_id. "
                "Nur neue Assets; Vorschau vor Übernahme. Maximal 512 KiB / 200 Zeilen."
            ),
        },
    )


@inventory_page
@require_http_methods(["GET", "POST"])
def csv_preview(request, preview_id):
    preview = ImportPreview.objects.get(pk=preview_id, actor=request.user)
    if not any_action(request.user, "asset.import"):
        raise PermissionDenied
    if not preview.committed_at and preview.expires_at <= timezone.now():
        return render(
            request,
            "inventory/preview.html",
            {"error": "Die Vorschau ist abgelaufen. Bitte erneut hochladen."},
        )
    if request.method == "GET":
        try:
            if preview.committed_at:
                for asset_id in preview.created_asset_ids:
                    services.read_asset(request.user, asset_id, "asset.import")
            else:
                for row in preview.rows:
                    csvio.validate_row(request.user, row)
        except ValidationError:
            return render(
                request,
                "inventory/preview.html",
                {"error": "Vorschau nicht mehr aktuell. Bitte erneut prüfen."},
            )
    if request.method == "POST":
        try:
            ids = csvio.commit_import(request.user, preview.pk)
            messages.success(request, f"{len(ids)} Assets importiert.")
            return redirect("asset_list")
        except ValidationError as exc:
            return render(
                request,
                "inventory/preview.html",
                {"preview": preview, "error": " ".join(exc.messages)},
            )
    return render(request, "inventory/preview.html", {"preview": preview})


@inventory_page
@require_http_methods(["GET"])
def csv_export(request):
    if not any_action(request.user, "asset.export"):
        raise PermissionDenied
    response = HttpResponse(
        csvio.export_csv(
            request.user,
            filtered_assets(request),
            include_private=request.GET.get("private") == "1",
        ),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="deelvo-inventory.csv"'
    return response
