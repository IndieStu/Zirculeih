import csv
import io
from datetime import date, timedelta
from functools import wraps
from uuid import uuid4

from accounts.authorization import allowed, authorization_write, require
from accounts.models import AuditEvent
from accounts.services import audit
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from inventory import services as inventory
from inventory.csvio import safe_cell
from inventory.forms import permitted_nodes
from inventory.models import Asset, Identifier, Location
from inventory.views import any_action

from . import forms, reports, services
from .models import Discrepancy, MaintenanceTask


def page(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.email_verified_at:
            raise Http404
        try:
            return view(request, *args, **kwargs)
        except (ObjectDoesNotExist, PermissionDenied, ValueError, TypeError) as exc:
            raise Http404 from exc

    return wrapped


def output_csv(name, columns, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(columns)
    writer.writerows([[safe_cell(c) for c in row] for row in rows])
    response = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{name}.csv"'
    return response


@page
@require_http_methods(["GET", "POST"])
def runs(request):
    if not any(any_action(request.user, a) for a in ["inventory_run.read", "inventory_run.create"]):
        raise PermissionDenied
    form = forms.RunForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            run = services.create_run(
                request.user,
                form.cleaned_data["title"],
                form.cleaned_data["scope"],
                form.cleaned_data["scope_id"],
            )
            return redirect("inventory_run", run_id=run.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "assetops/runs.html",
        dict(
            form=form,
            rows=Paginator(services.visible_runs(request.user), 30).get_page(
                request.GET.get("page")
            ),
            can_create=any_action(request.user, "inventory_run.create"),
        ),
    )


@page
@require_http_methods(["GET", "POST"])
def run_detail(request, run_id):
    run = services.read_run(request.user, run_id)
    scope = services.run_scope(run)
    message = ""
    initial = {
        "request_key": uuid4(),
        "namespace": request.POST.get("namespace"),
        "location": request.POST.get("location"),
    }
    scan = forms.ScanForm(
        request.user,
        request.POST if request.POST.get("action") == "scan" else None,
        initial=initial,
    )
    if request.method == "POST":
        try:
            action = request.POST.get("action")
            if action == "start":
                services.start(request.user, run.pk, int(request.POST.get("revision", "0")))
                return redirect("inventory_run", run_id=run.pk)
            if action in {"complete", "cancel"}:
                services.close(
                    request.user,
                    run.pk,
                    int(request.POST.get("revision", "0")),
                    cancel=action == "cancel",
                )
                return redirect("inventory_run", run_id=run.pk)
            if action == "scan" and scan.is_valid():
                data = scan.cleaned_data
                row, state = services.observe(
                    request.user,
                    run.pk,
                    data["namespace"].pk,
                    data["code"],
                    data["location"].pk,
                    data["request_key"],
                )
                labels = {
                    "seen": "Erwartet und gefunden",
                    "already_seen": "Bereits gesehen; keine doppelte Zählung",
                    "wrong_location": "Abweichender Fundort; Standort unverändert",
                    "unexpected": "Unerwarteter Fund; Erwartung unverändert",
                }
                message = row.asset.inventory_number + ": " + labels[state]
                scan = forms.ScanForm(request.user, initial=initial)
        except ValidationError as exc:
            message = " ".join(exc.messages)
    with authorization_write():
        run = services.read_run(request.user, run.pk)
        data = (
            run.report
            if run.status in {"completed", "cancelled"}
            else services.assessment(request.user, run)
            if run.status == "active"
            else {"assets": []}
        )
    draft_preview = []
    draft_error = ""
    if run.status == "draft":
        try:
            draft_preview = list(services.members(run)[: services.MAX_ASSETS + 1])
            services.check_assets(request.user, draft_preview)
            if len(draft_preview) > services.MAX_ASSETS:
                draft_preview = []
                draft_error = "Mehr als 2000 Assets: engeren Bereich wählen."
        except PermissionDenied:
            draft_preview = []
            draft_error = "Der gewählte Bestand ist nicht vollständig lesbar. Rechte prüfen."
    counts = {
        key: sum(r["outcome"] == key for r in data["assets"])
        for key in ["seen", "not_seen", "wrong_location", "unexpected"]
    }
    return render(
        request,
        "assetops/run.html",
        dict(
            run=run,
            draft_preview=draft_preview,
            draft_error=draft_error,
            scan=scan,
            message=message,
            report=data,
            counts=counts,
            report_rows=Paginator(data["assets"], 50).get_page(request.GET.get("page")),
            expected_count=run.expected.count(),
            discrepancies=run.discrepancies.select_related("asset").order_by(
                "asset__inventory_number"
            ),
            can_start=allowed(request.user, "inventory_run.start", scope),
            can_scan=allowed(request.user, "inventory_run.observe", scope),
            can_close=allowed(request.user, "inventory_run.complete", scope),
            can_export=allowed(request.user, "inventory_run.export", scope),
        ),
    )


@page
@require_http_methods(["GET"])
def run_export(request, run_id):
    with authorization_write():
        run = services.read_run(request.user, run_id, "inventory_run.export")
        services.read_run(request.user, run_id)
        data = run.report if run.closed_at else services.assessment(request.user, run)
        audit(request.user, "inventory_run.exported", object_id=run.pk)
        return output_csv(
            "deelvo-inventur",
            [
                "Inventarnummer",
                "Name",
                "Ergebnis",
                "Erwarteter Ort",
                "Fundorte",
                "Gewahrsam",
                "Bewertungszeit",
            ],
            [
                [
                    r["inventory_number"],
                    r["name"],
                    r["outcome"],
                    r["expected_location"],
                    ";".join(r["observed_locations"]),
                    r["custody"]["state"],
                    data["cutoff"],
                ]
                for r in data["assets"]
            ],
        )


@page
@require_http_methods(["GET", "POST"])
def discrepancy(request, discrepancy_id):
    row = Discrepancy.objects.select_related("asset", "run").get(pk=discrepancy_id)
    services.read_run(request.user, row.run_id)
    asset = inventory.read_asset(request.user, row.asset_id)
    require(request.user, "inventory_discrepancy.resolve", inventory.asset_scope(asset))
    message = ""
    if request.method == "POST":
        try:
            services.resolve(
                request.user,
                row.pk,
                request.POST.get("decision"),
                request.POST.get("reason", ""),
                int(request.POST.get("revision", "0")),
                location_id=request.POST.get("location"),
                asset_revision=int(request.POST.get("asset_revision", "0")),
            )
            return redirect("inventory_run", run_id=row.run_id)
        except ValidationError as exc:
            message = " ".join(exc.messages)
    locations = Location.objects.filter(
        pk__in=row.run.observations.filter(asset=asset).values_list("location_id", flat=True)
    )
    locations = [
        n for n in locations if allowed(request.user, "location.read", inventory.tree_scope(n))
    ]
    return render(
        request,
        "assetops/discrepancy.html",
        dict(row=row, asset=asset, locations=locations, message=message),
    )


@page
@require_http_methods(["GET", "POST"])
def maintenance(request):
    if not any_action(request.user, "maintenance.manage"):
        raise PermissionDenied
    form = forms.TaskForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            d = form.cleaned_data
            task = services.task_create(
                request.user,
                d["asset"].pk,
                d["title"],
                d["kind"],
                d["description"],
                d["due_date"],
                d["interval_days"],
                request.user if d["assign_self"] else None,
            )
            return redirect("maintenance_task", task_id=task.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    ids = (
        inventory.visible_assets(request.user, "maintenance.manage")
        .filter(pk__in=inventory.visible_assets(request.user))
        .values_list("pk", flat=True)
    )
    rows = (
        MaintenanceTask.objects.filter(asset_id__in=ids)
        .select_related("asset")
        .order_by("due_date", "id")
    )
    if request.GET.get("status") in {"planned", "in_progress", "completed", "cancelled"}:
        rows = rows.filter(status=request.GET["status"])
    if request.GET.get("overdue") == "1":
        rows = rows.filter(due_date__lt=timezone.localdate(), status__in=["planned", "in_progress"])
    return render(
        request,
        "assetops/maintenance.html",
        dict(form=form, rows=Paginator(rows, 30).get_page(request.GET.get("page"))),
    )


@page
@require_http_methods(["GET", "POST"])
def task(request, task_id):
    row = services.task_read(request.user, task_id)
    message = ""
    if request.method == "POST":
        try:
            if request.POST.get("action") == "attach":
                from inventory.extensions import read_media

                with authorization_write():
                    row = services.task_read(request.user, task_id)
                    require(request.user, "asset.attach", inventory.asset_scope(row.asset))
                    media = read_media(request.user, request.POST.get("media"))
                    if row.status in {"completed", "cancelled"} or media.asset_id != row.asset_id:
                        raise ValidationError("Dokument oder Auftrag nicht bearbeitbar.")
                    row.attachments.add(media)
                    audit(
                        request.user,
                        "maintenance.attachment_added",
                        object_id=row.asset_id,
                        details={"task": str(row.pk), "media": str(media.pk)},
                    )
            else:
                services.task_transition(
                    request.user,
                    row.pk,
                    int(request.POST.get("revision", "0")),
                    request.POST.get("action"),
                    request.POST.get("resolution", ""),
                    request.POST.get("condition") or None,
                    request.POST.get("release") == "on",
                )
            return redirect("maintenance_task", task_id=row.pk)
        except ValidationError as exc:
            message = " ".join(exc.messages)
    from inventory.extensions import read_media

    media = []
    for item in row.asset.media.filter(archived_at__isnull=True):
        try:
            media.append(read_media(request.user, item.pk))
        except PermissionDenied:
            continue
    return render(
        request,
        "assetops/task.html",
        dict(
            row=row,
            message=message,
            media=media,
            attached={m.pk for m in row.attachments.all()},
            conditions=Asset.Condition.choices,
            events=AuditEvent.objects.filter(
                object_id=str(row.asset_id), details__task=str(row.pk)
            ).order_by("-created_at"),
        ),
    )


@page
@require_http_methods(["GET", "POST"])
def bulk(request):
    if not any_action(request.user, "asset.move") and not any_action(request.user, "asset.manage"):
        raise PermissionDenied
    form = forms.BulkForm(request.user, request.POST or None)
    preview = None
    error = ""
    if request.method == "POST":
        try:
            if request.POST.get("commit"):
                d = signing.loads(
                    request.POST.get("preview", ""), salt="deelvo-bulk-v1", max_age=600
                )
                if d["actor"] != str(request.user.pk):
                    raise PermissionDenied
                services.bulk(
                    request.user,
                    d["entries"],
                    d["action"],
                    reason=d["reason"],
                    location_id=d["location"],
                    condition=d["condition"],
                )
                return redirect("asset_list")
            if form.is_valid():
                d = form.cleaned_data
                data = dict(
                    actor=str(request.user.pk),
                    entries=[dict(id=str(a.pk), revision=a.revision) for a in d["assets"]],
                    action=d["action"],
                    reason=d["reason"],
                    location=str(d["location"].pk) if d["location"] else None,
                    condition=d["condition"],
                )
                preview = dict(
                    token=signing.dumps(data, salt="deelvo-bulk-v1"),
                    assets=list(d["assets"]),
                    location=d["location"],
                    data=data,
                )
        except (ValidationError, signing.BadSignature) as exc:
            error = (
                " ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else "Vorschau ungültig oder abgelaufen; neu prüfen."
            )
    return render(request, "assetops/bulk.html", dict(form=form, preview=preview, message=error))


@page
@require_http_methods(["GET"])
def reporting(request):
    try:
        start = date.fromisoformat(
            request.GET.get("start", (timezone.localdate() - timedelta(days=30)).isoformat())
        )
        end = date.fromisoformat(request.GET.get("end", timezone.localdate().isoformat()))
        with authorization_write():
            data = reports.aggregate(
                request.user,
                start,
                end,
                location_id=request.GET.get("location") or None,
                category_id=request.GET.get("category") or None,
                export=request.GET.get("export") == "1",
            )
            if request.GET.get("export") == "1":
                audit(request.user, "asset.operations_report_exported")
                rows = [
                    ["Aktueller Bestand", data["asset_count"]],
                    ["Offene Ausleihpositionen", data["open_loans"]],
                    ["Überfällig", data["overdue"]],
                    ["Offene Wartung", data["maintenance_open"]],
                ]
                rows += [["Standort: " + k, v] for k, v in data["by_location"]]
                rows += [["Kategorie: " + k, v] for k, v in data["by_category"]]
                rows += [
                    ["Reservierte Stunden: " + k, round(v["reserved_hours"], 2)]
                    for k, v in data["bookings"]
                ]
                return output_csv("deelvo-betriebsbericht", ["Kennzahl", "Wert"], rows)
        error = ""
    except ValidationError as exc:
        data = {}
        error = " ".join(exc.messages)
        start = end = timezone.localdate()
    query = request.GET.copy()
    query["export"] = "1"
    return render(
        request,
        "assetops/reports.html",
        dict(
            data=data,
            message=error,
            start=start,
            end=end,
            export_query=query.urlencode(),
            locations=permitted_nodes(request.user, Location, "location.read"),
        ),
    )


@page
@require_http_methods(["GET"])
def label_svg(request, identifier_id):
    import qrcode
    from qrcode.image.svg import SvgPathImage

    row = Identifier.objects.select_related("namespace").get(
        pk=identifier_id, is_active=True, asset__isnull=False, namespace__is_active=True
    )
    asset = inventory.read_asset(request.user, row.asset_id)
    require(request.user, "identifier.resolve", inventory.asset_scope(asset))
    image = qrcode.make(row.canonical_value, image_factory=SvgPathImage, border=4)
    response = HttpResponse(image.to_string(), content_type="image/svg+xml")
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@page
@require_http_methods(["GET"])
def labels(request):
    ids = request.GET.getlist("asset")
    if not ids:
        return render(
            request,
            "assetops/label_select.html",
            {"assets": inventory.visible_assets(request.user)[:2000]},
        )
    if not 1 <= len(ids) <= 100:
        raise Http404
    rows = []
    for pk in dict.fromkeys(ids):
        asset = inventory.read_asset(request.user, pk)
        require(request.user, "identifier.resolve", inventory.asset_scope(asset))
        code = asset.identifiers.get(
            kind="owned", is_active=True, namespace__key="deelvo", namespace__is_active=True
        )
        rows.append(dict(asset=asset, code=code))
    return render(request, "assetops/labels.html", dict(rows=rows))


@page
@require_http_methods(["GET", "POST"])
def terminal_home(request):
    from . import terminal

    terminal.require_staff(request)
    if request.method == "POST":
        if request.POST.get("action") == "leave":
            prior = request.session.pop("staffed_terminal", None)
            if prior:
                from .models import StaffedContext

                StaffedContext.objects.filter(pk=prior["id"], owner=request.user).update(
                    revoked=True
                )
            request.session.pop("lending_cart", None)
            return redirect("inventory_dashboard")
        mode = request.POST.get("mode", "lookup")
        if mode not in {"lookup", "inventory", "checkout", "return"}:
            raise Http404
        action = {
            "lookup": "identifier.resolve",
            "inventory": "inventory_run.observe",
            "checkout": "loan.checkout",
            "return": "loan.return",
        }[mode]
        if not any_action(request.user, action):
            raise PermissionDenied
        terminal.reset(request, mode)
        if mode == "checkout":
            return redirect("loan_checkout")
        if mode == "return":
            return redirect("loan_return_scan")
        return redirect("staffed_terminal")
    return render(
        request,
        "assetops/terminal.html",
        dict(
            scan=forms.ScanForm(request.user, initial={"request_key": uuid4()}),
            runs=[r for r in services.visible_runs(request.user) if r.status == "active"],
            modes=[
                (key, label)
                for key, label, action in [
                    ("lookup", "Code nachschlagen", "identifier.resolve"),
                    ("inventory", "Inventur", "inventory_run.observe"),
                    ("checkout", "Ausgabe vorbereiten", "loan.checkout"),
                    ("return", "Rücknahme vorbereiten", "loan.return"),
                ]
                if any_action(request.user, action)
            ],
        ),
    )


@page
@require_http_methods(["POST"])
def terminal_scan(request):
    terminal = request.session.get("staffed_terminal")
    if not terminal or terminal["mode"] not in {"inventory", "lookup"}:
        raise PermissionDenied
    message = ""
    status = 200
    form = forms.ScanForm(request.user, request.POST)
    if terminal["mode"] == "lookup":
        form.fields["location"].required = False
    if form.is_valid():
        d = form.cleaned_data
        try:
            if terminal["mode"] == "inventory":
                row, state = services.observe(
                    request.user,
                    request.POST.get("run"),
                    d["namespace"].pk,
                    d["code"],
                    d["location"].pk,
                    d["request_key"],
                )
                message = (
                    row.asset.inventory_number
                    + " · "
                    + {
                        "seen": "Gefunden",
                        "already_seen": "Bereits gesehen",
                        "wrong_location": "Abweichender Fundort; Standort unverändert",
                        "unexpected": "Unerwarteter Fund",
                    }[state]
                )
            else:
                result = inventory.resolve_identifier(request.user, d["namespace"].pk, d["code"])
                message = (
                    "Objekt erkannt"
                    if result.status == "found"
                    else "Code unbekannt oder nicht zugänglich; weiter scannen."
                )
                if result.asset_id:
                    asset = inventory.read_asset(request.user, result.asset_id)
                    message = asset.inventory_number + " · " + asset.name
        except ValidationError as exc:
            status = 400
            message = " ".join(exc.messages)
    else:
        status = 400
        message = "Code, Namensraum und Beobachtungsort prüfen."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.http import JsonResponse

        return JsonResponse(
            {"message": message, "generation": terminal["generation"]}, status=status
        )
    return render(request, "assetops/terminal_result.html", dict(message=message))
