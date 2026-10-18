from uuid import uuid4

from accounts.authorization import allowed, authorization_write, require
from accounts.models import User
from accounts.services import audit
from bookings.models import Booking
from bookings.views import error_message, page
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from inventory.services import resolve_identifier
from inventory.views import any_action
from resources.models import ResourceUnit
from resources.services import resource_scope, visible_resources

from . import agreements, forms, services
from .models import Agreement, IdentityCheck, Loan, LoanLine


def error(form, exc):
    form.add_error(None, error_message(exc))


@page
@require_http_methods(["GET", "POST"])
def agreement_list(request):
    resource_id = request.GET.get("resource")
    versions = []
    if resource_id:
        try:
            from uuid import UUID

            resource_id = UUID(resource_id)
        except (ValueError, TypeError) as exc:
            raise Http404 from exc
        resource = visible_resources(request.user).filter(pk=resource_id).first()
        if resource is None:
            raise Http404
        try:
            units = list(resource.units.filter(is_active=True).select_related("asset"))
            for unit in units:
                versions.extend(agreements.required_versions(resource, unit.asset))
        except ValidationError:
            pass
    else:
        for row in Agreement.objects.filter(kind__in=["general", "insurance"], is_active=True):
            version = row.versions.filter(published_at__isnull=False).order_by("-number").first()
            if version:
                versions.append(version)
    versions = list({v.pk: v for v in versions}.values())
    message = ""
    if request.method == "POST":
        ids = request.POST.getlist("versions")
        if not ids or not set(ids).issubset({str(v.pk) for v in versions}):
            message = "Bitte die angezeigten Textversionen bewusst auswählen."
        else:
            try:
                agreements.accept(request.user, ids)
                message = "Die ausgewählten Versionen wurden bestätigt."
            except ValidationError as exc:
                message = error_message(exc)
    from .models import Acceptance

    accepted = set(
        Acceptance.objects.filter(user=request.user, version__in=versions).values_list(
            "version_id", flat=True
        )
    )
    for version in versions:
        version.accepted = version.pk in accepted
    return render(
        request,
        "lending/agreements.html",
        {
            "versions": versions,
            "message": message,
            "has_pending": any(not v.accepted for v in versions),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def agreement_admin(request):
    require(request.user, "agreement.edit")
    form = forms.AgreementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with authorization_write():
            row = agreements.create_agreement(
                request.user, form.cleaned_data["title"], form.cleaned_data["kind"]
            )
            agreements.save_version(request.user, row.pk, form.cleaned_data["text"])
        return redirect("agreement_admin")
    return render(
        request,
        "lending/agreement_admin.html",
        {
            "form": form,
            "agreements": Agreement.objects.prefetch_related("versions"),
            "can_publish": allowed(request.user, "agreement.publish"),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def version_add(request, agreement_id):
    require(request.user, "agreement.edit")
    row = Agreement.objects.get(pk=agreement_id)
    form = forms.VersionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        agreements.save_version(request.user, row.pk, form.cleaned_data["text"])
        return redirect("agreement_admin")
    return render(
        request, "bookings/form.html", {"title": "Neue Version: " + row.title, "form": form}
    )


@page
@require_POST
def version_publish(request, version_id):
    try:
        agreements.publish_version(request.user, version_id)
    except ValidationError as exc:
        messages.error(request, error_message(exc))
    return redirect("agreement_admin")


@page
@require_http_methods(["GET", "POST"])
def assignment(request):
    if not any_action(request.user, "agreement.assign"):
        raise PermissionDenied
    form = forms.AssignmentForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            agreements.assign(
                request.user,
                form.cleaned_data["agreement"].pk,
                resource=form.cleaned_data["resource"],
                asset=form.cleaned_data["asset"],
            )
            return redirect("agreement_assignment")
        except ValidationError as exc:
            error(form, exc)
    return render(
        request, "bookings/form.html", {"title": "Zusatzvereinbarung zuordnen", "form": form}
    )


@page
@require_http_methods(["GET"])
def own(request):
    return render(
        request,
        "lending/list.html",
        {
            "title": "Meine Ausleihen",
            "page_obj": Paginator(services.visible_loans(request.user), 30).get_page(
                request.GET.get("page")
            ),
        },
    )


@page
@require_http_methods(["GET"])
def detail(request, loan_id):
    try:
        loan = services.read_loan(request.user, loan_id)
    except Loan.DoesNotExist as exc:
        raise Http404 from exc
    lines = list(loan.lines.select_related("booking__resource", "asset"))
    for line in lines:
        condition_labels = {
            "good": "Gut",
            "worn": "Gebraucht",
            "damaged": "Beschädigt",
            "inspection": "Prüfung erforderlich",
        }
        line.issue_condition_label = condition_labels.get(
            line.issue_condition, line.issue_condition
        )
        line.return_condition_label = condition_labels.get(
            line.return_condition, line.return_condition
        )
        line.overdue = not line.returned_at and line.expected_return < timezone.now()
        line.can_return = not line.returned_at and allowed(
            request.user, "loan.return", resource_scope(line.booking.resource)
        )
        line.can_extend = not line.returned_at and allowed(
            request.user, "loan.extend", resource_scope(line.booking.resource)
        )
    return render(request, "lending/detail.html", {"loan": loan, "lines": lines})


@page
@require_http_methods(["GET", "POST"])
def line_return(request, line_id):
    try:
        line = LoanLine.objects.select_related("booking__resource", "loan").get(pk=line_id)
    except LoanLine.DoesNotExist as exc:
        raise Http404 from exc
    require(request.user, "loan.return", resource_scope(line.booking.resource))
    form = forms.ReturnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        key = data.pop("key")
        try:
            services.return_lines(request.user, line.loan_id, {str(line.pk): data}, key)
            from assetops.terminal import rotate

            rotate(request)
            messages.success(
                request,
                "Gegenstand zurückgenommen. Nächsten Code scannen oder Ausleihbeleg öffnen.",
            )
            return redirect("loan_return_scan")
        except ValidationError as exc:
            error(form, exc)
    return render(
        request,
        "bookings/form.html",
        {"title": "Gegenstand zurücknehmen: " + line.asset.name, "form": form},
    )


@page
@require_http_methods(["GET", "POST"])
def operations(request):
    if not any(any_action(request.user, a) for a in ("loan.read", "loan.checkout", "loan.return")):
        raise PermissionDenied
    rows = services.visible_loans(request.user, operational=True)
    overdue = LoanLine.objects.filter(
        loan__in=rows, returned_at__isnull=True, expected_return__lt=timezone.now()
    )
    pending = list(services.pickup_bookings(request.user)[:30])
    for row in pending:
        row.can_no_show = (
            allowed(request.user, "booking.manage_all", resource_scope(row.resource))
            and timezone.now() >= row.appointment.pickup_at
        )
    return render(
        request,
        "lending/operations.html",
        {
            "loans": Paginator(rows, 30).get_page(request.GET.get("page")),
            "pickups": pending,
            "overdue": overdue,
            "can_checkout": any_action(request.user, "loan.checkout"),
            "can_return": any_action(request.user, "loan.return"),
            "can_agreements": allowed(request.user, "agreement.edit"),
            "can_assign": any_action(request.user, "agreement.assign"),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def checkout(request):
    require(request.user, "borrower.read_contact")
    if not any_action(request.user, "loan.checkout"):
        raise PermissionDenied
    cart = request.session.get(
        "lending_cart",
        {"actor": str(request.user.pk), "borrower": "", "bookings": [], "key": str(uuid4())},
    )
    if cart["actor"] != str(request.user.pk):
        cart = {"actor": str(request.user.pk), "borrower": "", "bookings": [], "key": str(uuid4())}
    cart.setdefault("units", [])
    form = forms.ScanForm(
        request.POST if request.POST.get("action") == "scan" else None,
        initial={"namespace": cart.get("namespace")},
    )
    message = ""
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "reset":
            from assetops.terminal import rotate

            rotate(request)
            request.session.pop("lending_cart", None)
            return redirect("loan_checkout")
        if action == "person":
            person = User.objects.filter(
                email__iexact=request.POST.get("email", "").strip(),
                is_active=True,
                email_verified_at__isnull=False,
            ).first()
            if person:
                from assetops.terminal import rotate

                rotate(request)
                cart.update(borrower=str(person.pk), bookings=[], units=[], key=str(uuid4()))
                audit(request.user, "borrower.contact_read", subject=person)
            else:
                message = "Kein freigegebenes verifiziertes Konto gefunden."
        if (
            action == "identity"
            and cart["borrower"]
            and request.POST.get("identity_confirm") == "on"
        ):
            services.identity_check(request.user, cart["borrower"])
            message = "Erst-Ausweisprüfung dokumentiert; keine Ausweisdaten gespeichert."
        if action == "scan" and form.is_valid() and cart["borrower"]:
            result = resolve_identifier(
                request.user, form.cleaned_data["namespace"].pk, form.cleaned_data["code"]
            )
            row = (
                Booking.objects.filter(
                    beneficiary_id=cart["borrower"], unit_id=result.unit_id, status="confirmed"
                )
                .order_by("start")
                .first()
                if result.status == "found"
                else None
            )
            if row and allowed(request.user, "loan.checkout", resource_scope(row.resource)):
                if str(row.pk) in cart["bookings"]:
                    message = "Bereits vorbereitet; kein zweiter Eintrag."
                elif len(cart["bookings"]) < 50:
                    cart["bookings"].append(str(row.pk))
                    message = "Reservierung vorbereitet. Ausgabe erst nach Bestätigung."
            else:
                message = "Keine passende Reservierung gefunden."
                if result.unit_id:
                    unit = ResourceUnit.objects.select_related("resource").get(pk=result.unit_id)
                    if allowed(request.user, "loan.checkout", resource_scope(unit.resource)):
                        uid = str(unit.pk)
                        if uid in cart["units"]:
                            message = "Bereits vorbereitet; kein Duplikat."
                        elif len(cart["units"]) + len(cart["bookings"]) < 50:
                            cart["units"].append(uid)
                            message = (
                                "Spontanausleihe vorbereitet. "
                                "Zeitraum und Bedingungen vor Abschluss prüfen."
                            )
            cart["namespace"] = str(form.cleaned_data["namespace"].pk)
            form = forms.ScanForm(initial={"namespace": cart["namespace"]})
        if action == "confirm" and cart["borrower"]:
            checks = {
                bid: {
                    "condition": request.POST.get("condition_" + bid),
                    "accessories_checked": request.POST.get("checked_" + bid) == "on",
                    "accessories": request.POST.get("accessories_" + bid, ""),
                }
                for bid in cart["bookings"]
            }
            from bookings.forms import BookingForm

            pending = []
            valid = True
            for uid in cart["units"]:
                unit = ResourceUnit.objects.select_related("resource__bookingpolicy").get(pk=uid)
                entry = BookingForm(
                    unit.resource.bookingpolicy,
                    request.POST,
                    prefix="u_" + uid,
                    choose_capacity=False,
                )
                if not entry.is_valid():
                    valid = False
                    message = "Bitte alle Zeiträume und Termine gültig ausfüllen."
                    break
                data = entry.cleaned_data
                pending.append(
                    {
                        "unit_id": uid,
                        "start": data["start"],
                        "end": data["end"],
                        "key": data["key"],
                        "pickup_at": data.get("pickup_at"),
                        "return_at": data.get("return_at"),
                        "start_fold": data.get("start_fold"),
                        "end_fold": data.get("end_fold"),
                    }
                )
                checks[uid] = {
                    "condition": request.POST.get("condition_" + uid),
                    "accessories_checked": request.POST.get("checked_" + uid) == "on",
                    "accessories": request.POST.get("accessories_" + uid, ""),
                }
            try:
                if not valid:
                    raise ValidationError(message)
                loan = services.checkout(
                    request.user,
                    cart["borrower"],
                    cart["bookings"],
                    cart["key"],
                    checks=checks,
                    spontaneous=pending,
                )
                request.session.pop("lending_cart", None)
                if request.session.get("staffed_terminal"):
                    from assetops.terminal import reset

                    reset(request, "checkout")
                    messages.success(
                        request,
                        "Ausgabe abgeschlossen. Vorbereitung für die nächste Person geleert.",
                    )
                    return redirect("loan_checkout")
                return redirect("loan_detail", loan_id=loan.pk)
            except ValidationError as exc:
                message = error_message(exc)
    request.session["lending_cart"] = cart
    person = User.objects.filter(pk=cart["borrower"]).first() if cart["borrower"] else None
    rows = []
    for bid in cart["bookings"]:
        row = Booking.objects.select_related("resource", "unit__asset").get(
            pk=bid, beneficiary_id=cart["borrower"]
        )
        require(request.user, "loan.checkout", resource_scope(row.resource))
        rows.append(row)
    from bookings.forms import BookingForm

    pending_units = []
    for uid in cart["units"]:
        unit = ResourceUnit.objects.select_related("resource__bookingpolicy").get(pk=uid)
        require(request.user, "loan.checkout", resource_scope(unit.resource))
        pending_units.append(
            {
                "unit": unit,
                "form": BookingForm(
                    unit.resource.bookingpolicy,
                    request.POST if request.POST.get("action") == "confirm" else None,
                    prefix="u_" + uid,
                    choose_capacity=False,
                ),
            }
        )
    return render(
        request,
        "lending/checkout.html",
        {
            "form": form,
            "person": person,
            "bookings": rows,
            "message": message,
            "identity_needed": person and not IdentityCheck.objects.filter(user=person).exists(),
            "can_identity": allowed(request.user, "loan.inspect_identity"),
            "pending_units": pending_units,
        },
    )


@page
@require_http_methods(["GET", "POST"])
def return_scan(request):
    if not any_action(request.user, "loan.return"):
        raise PermissionDenied
    form = forms.ScanForm(request.POST or None)
    message = ""
    if request.method == "POST" and form.is_valid():
        result = resolve_identifier(
            request.user, form.cleaned_data["namespace"].pk, form.cleaned_data["code"]
        )
        line = (
            LoanLine.objects.filter(asset_id=result.asset_id, returned_at__isnull=True)
            .select_related("booking__resource")
            .first()
            if result.status == "found"
            else None
        )
        if line and allowed(request.user, "loan.return", resource_scope(line.booking.resource)):
            return redirect("loan_return", line_id=line.pk)
        message = (
            "Kein berechtigt rücknehmbarer offener Gegenstand gefunden. Weiter scannen möglich."
        )
    return render(request, "lending/scan.html", {"form": form, "message": message})


@page
@require_http_methods(["GET", "POST"])
def extend(request, line_id):
    from bookings.models import BookingPolicy

    line = LoanLine.objects.select_related("booking__resource", "loan").get(pk=line_id)
    require(request.user, "loan.extend", resource_scope(line.booking.resource))
    policy = BookingPolicy.objects.get(resource=line.booking.resource)
    form = forms.ExtensionForm(
        policy, request.POST or None, initial={"revision": line.booking.revision}
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.extend_line(
                request.user,
                line.pk,
                data["end"],
                data["return_at"],
                data["revision"],
                data["reason"],
                end_fold=data.get("end_fold"),
            )
            return redirect("loan_detail", loan_id=line.loan_id)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(
                None,
                error_message(exc)
                if isinstance(exc, ValidationError)
                else "Folgebelegung verhindert die Verlängerung.",
            )
    return render(
        request,
        "bookings/form.html",
        {
            "title": "Ausleihe verlängern: " + line.booking.resource.title,
            "form": form,
            "text": "Bei einem Bundle gilt die Verlängerung gemeinsam "
            "für alle noch offenen Komponenten. "
            "Alle Voraussetzungen werden erneut geprüft."
            if hasattr(line.booking, "bundle_member")
            else None,
        },
    )


@page
@require_http_methods(["GET", "POST"])
def no_show(request, booking_id):
    from bookings.forms import ReasonForm

    row = Booking.objects.select_related("resource").get(pk=booking_id)
    require(request.user, "loan.checkout", resource_scope(row.resource))
    require(request.user, "booking.manage_all", resource_scope(row.resource))
    form = ReasonForm(request.POST or None, initial={"revision": row.revision})
    if request.method == "POST" and form.is_valid():
        try:
            services.no_show(
                request.user, row.pk, form.cleaned_data["revision"], form.cleaned_data["reason"]
            )
            return redirect("loan_operations")
        except ValidationError as exc:
            error(form, exc)
    return render(
        request,
        "bookings/form.html",
        {"title": "Als nicht abgeholt abschließen: " + row.resource.title, "form": form},
    )


@page
@require_POST
def unassign(request, assignment_id):
    agreements.unassign(request.user, assignment_id)
    return redirect("agreement_assignment")
