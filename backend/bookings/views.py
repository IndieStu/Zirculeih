from datetime import timedelta
from functools import wraps

from accounts.authorization import allowed, require
from accounts.ratelimit import take
from accounts.views import throttled
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from resources.models import Resource
from resources.services import resource_scope, visible_resources

from . import forms, services
from .models import (
    Booking,
    BookingIncident,
    BookingPolicy,
    ResourceBlock,
    ScheduleException,
    ScheduleWindow,
)

MESSAGES = {
    "borrower_profile_required": "Bitte zuerst dein Ausleihprofil vollständig ausfüllen.",
    "physical_unit_required": "Eine physische Einheit muss eingerichtet sein.",
    "pickup_unavailable": "Abholtermin außerhalb eines erlaubten Abholfensters oder Zeitraums.",
    "return_unavailable": "Der Rückgabetermin liegt nicht in einem erlaubten Rückgabefenster.",
    "available": ("Der Zeitraum ist frei."),
    "permission_denied": "Für diesen Zeitraum fehlt eine erforderliche Berechtigung.",
    "reserved": "Der Zeitraum ist inzwischen belegt.",
    "capacity_exhausted": "Keine geeignete aktive Einheit vorhanden.",
    "not_configured": "Buchung noch nicht eingerichtet.",
    "not_bookable": "Dieses Angebot kann derzeit nicht reserviert werden.",
    "invalid_interval": "Beginn, Ende oder Mindestvorlauf passen nicht.",
    "duration_not_allowed": "Die erlaubte Nutzungsdauer wird nicht eingehalten.",
    "outside_booking_horizon": "Der Zeitraum liegt außerhalb des Buchungshorizonts.",
    "granularity_not_allowed": "Bitte das konfigurierte Zeitraster einhalten.",
    "outside_usage_hours": "Außerhalb der Nutzungszeiten.",
    "outside_access_hours": "Außerhalb des Gebäudezugangs.",
    "outside_staffed_hours": (
        "Außerhalb der betreuten Öffnung und kein passendes Recht zur unbetreuten Nutzung."
    ),
    "hard_block": "In diesem Zeitraum besteht eine harte Sperre.",
    "parallel_limit": "Das Limit gleichzeitig laufender Buchungen ist erreicht.",
    "lending_setup_required": (
        "Physische Ausleihreservierungen sind für dieses Angebot noch nicht "
        "freigeschaltet. Bitte beim Team melden."
    ),
    "qualification_required": "Die erforderliche Einweisung fehlt. Bitte wende dich an das Team.",
    "agreement_required": "Bitte die erforderlichen aktuellen Vereinbarungen bestätigen.",
}


def page(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        try:
            services.require_active_actor(request.user)
            return view(request, *args, **kwargs)
        except (
            ObjectDoesNotExist,
            PermissionDenied,
            Booking.DoesNotExist,
            Resource.DoesNotExist,
            BookingPolicy.DoesNotExist,
            ResourceBlock.DoesNotExist,
            ScheduleWindow.DoesNotExist,
            ScheduleException.DoesNotExist,
            BookingIncident.DoesNotExist,
        ) as exc:
            raise Http404 from exc

    return wrapped


def error_message(exc):
    return " ".join(MESSAGES.get(message, message) for message in exc.messages)


@page
@require_http_methods(["GET", "POST"])
def create(request, resource_id):
    resource = get_object_or_404(visible_resources(request.user), pk=resource_id)
    policy = BookingPolicy.objects.filter(resource=resource).first()
    if policy is None:
        return render(
            request,
            "bookings/unavailable.html",
            {"resource": resource, "message": MESSAGES["not_configured"]},
        )
    from django import forms as django_forms
    from lending import agreements
    from resources.requirements import outstanding

    try:
        missing_versions, missing_qualifications = outstanding(request.user, resource)
    except ValidationError:
        missing_versions, missing_qualifications = [], []
    initial = {
        key: request.GET[key]
        for key in ("start", "end", "pickup_at", "return_at")
        if key in request.GET
    }
    form = forms.BookingForm(policy, request.POST or None, initial=initial)
    requirement_fields = []
    for version in missing_versions:
        key = "agreement_" + str(version.pk)
        form.fields[key] = django_forms.BooleanField(
            label="Ich akzeptiere " + version.agreement.title + ".", required=False
        )
        requirement_fields.append((version, form[key]))
    result = None
    if request.method == "POST":
        if not take(request, "booking-submit", str(request.user.pk), limit=120):
            return throttled()
        if form.is_valid():
            data = form.cleaned_data
            try:
                kwargs = {"start_fold": data["start_fold"], "end_fold": data["end_fold"]}
                if policy.use_mode == "physical_loan":
                    kwargs.update(pickup_at=data["pickup_at"], return_at=data["return_at"])
                if request.POST.get("action") == "confirm":
                    if any(not data["agreement_" + str(v.pk)] for v in missing_versions):
                        raise ValidationError("Bitte die erforderlichen Vereinbarungen bestätigen.")
                    if missing_versions:
                        agreements.accept(request.user, [v.pk for v in missing_versions])
                    booking = services.confirm(
                        request.user, resource.pk, data["start"], data["end"], data["key"], **kwargs
                    )
                    return redirect("booking_detail", booking_id=booking.pk)
                result = services.availability(
                    request.user, resource.pk, data["start"], data["end"], **kwargs
                )
            except ValidationError as exc:
                form.add_error(None, error_message(exc))
    return render(
        request,
        "bookings/create.html",
        {
            "resource": resource,
            "policy": policy,
            "form": form,
            "result": result,
            "requirement_fields": requirement_fields,
            "missing_qualifications": missing_qualifications,
            "booking_fields": [f for f in form if not f.name.startswith("agreement_")],
            "result_message": MESSAGES.get(result.code) if result else None,
        },
    )


@page
@require_http_methods(["GET"])
def own(request):
    rows = services.visible_bookings(request.user).select_related(
        "loan_line__loan", "loan_line__asset"
    )
    return render(
        request,
        "bookings/list.html",
        {
            "page_obj": Paginator(rows, 30).get_page(request.GET.get("page")),
            "title": "Meine Vorgänge",
        },
    )


@page
@require_http_methods(["GET"])
def detail(request, booking_id):
    booking = services.read_booking(request.user, booking_id)
    return render(
        request,
        "bookings/detail.html",
        {
            "booking": booking,
            "last_date": booking.end_date_exclusive - timedelta(days=1)
            if booking.end_date_exclusive
            else None,
            "can_cancel": booking.status == "confirmed"
            and timezone.now()
            < booking.start
            - timedelta(minutes=booking.policy_snapshot["cancellation_notice_minutes"])
            and allowed(
                request.user,
                "booking.cancel_own"
                if booking.beneficiary_id == request.user.pk
                else "booking.manage_all",
                resource_scope(booking.resource),
            ),
            "has_incident": booking.incidents.filter(is_open=True).exists(),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def cancel(request, booking_id):
    booking = services.read_booking(request.user, booking_id)
    form = forms.ReasonForm(request.POST or None, initial={"revision": booking.revision})
    if request.method == "POST" and form.is_valid():
        try:
            services.cancel(
                request.user, booking.pk, form.cleaned_data["revision"], form.cleaned_data["reason"]
            )
            return redirect("booking_detail", booking_id=booking.pk)
        except ValidationError as exc:
            form.add_error(None, error_message(exc))
    return render(request, "bookings/form.html", {"title": "Buchung stornieren", "form": form})


@page
@require_http_methods(["GET"])
def operations(request):
    from inventory.views import any_action

    if not any(
        any_action(request.user, a)
        for a in ("booking.read_all", "booking.configure", "booking.block")
    ):
        raise PermissionDenied
    rows = services.visible_bookings(request.user, operational=True)
    resources = list(Resource.objects.all())
    configs = [
        r for r in resources if allowed(request.user, "booking.configure", resource_scope(r))
    ]
    blocks = [
        b
        for b in ResourceBlock.objects.filter(is_active=True)
        if allowed(
            request.user, "booking.block", services.schedule_scope(b.resource_id, b.location_id)
        )
    ]
    windows = [
        w
        for w in ScheduleWindow.objects.all()
        if allowed(
            request.user,
            "booking.configure",
            services.schedule_scope(w.resource_id, w.location_id, w.category_id, w.organization),
        )
    ]
    exceptions = [
        w
        for w in ScheduleException.objects.all()
        if allowed(
            request.user,
            "booking.configure",
            services.schedule_scope(w.resource_id, w.location_id, w.category_id, w.organization),
        )
    ]
    incidents = BookingIncident.objects.filter(booking__in=rows, is_open=True).select_related(
        "booking__resource"
    )
    for incident in incidents:
        incident.can_resolve = allowed(
            request.user, "booking.manage_all", resource_scope(incident.booking.resource)
        )
    return render(
        request,
        "bookings/operations.html",
        {
            "page_obj": Paginator(rows, 30).get_page(request.GET.get("page")),
            "configs": configs,
            "blocks": blocks,
            "windows": windows,
            "exceptions": exceptions,
            "incidents": incidents,
            "can_configure": any_action(request.user, "booking.configure"),
            "can_block": any_action(request.user, "booking.block"),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def policy_edit(request, resource_id):
    resource = Resource.objects.get(pk=resource_id)
    require(request.user, "booking.configure", resource_scope(resource))
    policy = BookingPolicy.objects.filter(resource=resource).first() or BookingPolicy(
        resource=resource
    )
    form = forms.PolicyForm(request.POST or None, instance=policy)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        revision = data.pop("expected_revision")
        try:
            services.save_policy(request.user, resource.pk, data, revision)
            return redirect("booking_operations")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "bookings/form.html",
        {
            "title": f"Buchungsregeln: {resource.title}",
            "form": form,
            "text": (
                "Nutzung, Gebäudezugang und betreute Öffnung benötigen Zeitpläne. "
                "Physische Ausleihe und zusätzliche Pflichtgates bleiben bis zu "
                "ihren Phasen gesperrt."
            ),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def schedule_add(request, exception=False):
    from inventory.views import any_action

    if not any_action(request.user, "booking.configure"):
        raise PermissionDenied
    form = (forms.ExceptionForm if exception else forms.WindowForm)(
        request.user, request.POST or None, initial={"resource": request.GET.get("resource")}
    )
    if request.method == "POST" and form.is_valid():
        try:
            data = dict(form.cleaned_data)
            through = data.pop("through", None)
            from accounts.authorization import authorization_write

            with authorization_write():
                services.save_schedule(request.user, data, exception=exception)
                if exception and through:
                    day = data["date"] + timedelta(days=1)
                    while day <= through:
                        services.save_schedule(request.user, {**data, "date": day}, exception=True)
                        day += timedelta(days=1)
            return redirect("booking_operations")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "bookings/form.html",
        {
            "title": "Datumsbezogene Ausnahme" if exception else "Wochenzeitfenster hinzufügen",
            "form": form,
            "text": (
                "Genau einen Bereich wählen: Organisation, Kategorie, Standort oder Artikel / Raum."
                " "
                "Ausnahmen ersetzen "
                "Wochenzeiten am Datum. Ende am Folgetag erlaubt höchstens 24 "
                "Stunden; 00:00 bis 00:00 am Folgetag ist ein ganzer Tag."
            ),
        },
    )


@page
@require_POST
def schedule_remove(request, row_id, exception=False):
    services.remove_schedule(request.user, row_id, exception=exception)
    return redirect("booking_operations")


@page
@require_http_methods(["GET", "POST"])
def block_add(request):
    from inventory.views import any_action

    if not any_action(request.user, "booking.block"):
        raise PermissionDenied
    form = forms.BlockForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            data = {
                k: form.cleaned_data[k] for k in ("resource", "location", "start", "end", "reason")
            }
            services.set_block(request.user, data)
            return redirect("booking_operations")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "bookings/form.html",
        {
            "title": "Harte Sperre setzen",
            "form": form,
            "text": (
                "Bestehende Buchungen bleiben erhalten und werden zur Klärung "
                "markiert. Neue Bestätigungen werden gesperrt."
            ),
        },
    )


@page
@require_http_methods(["GET", "POST"])
def block_lift(request, block_id):
    row = ResourceBlock.objects.get(pk=block_id)
    require(
        request.user, "booking.block", services.schedule_scope(row.resource_id, row.location_id)
    )
    form = forms.ReasonForm(request.POST or None, initial={"revision": row.revision})
    if request.method == "POST" and form.is_valid():
        try:
            services.lift_block(
                request.user, row.pk, form.cleaned_data["revision"], form.cleaned_data["reason"]
            )
            return redirect("booking_operations")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "bookings/form.html", {"title": "Harte Sperre aufheben", "form": form})


@page
@require_http_methods(["GET", "POST"])
def incident_resolve(request, incident_id):
    row = BookingIncident.objects.get(pk=incident_id)
    require(request.user, "booking.manage_all", resource_scope(row.booking.resource))
    form = forms.ReasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.resolve_incident(request.user, row.pk, form.cleaned_data["reason"])
            return redirect("booking_operations")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "bookings/form.html",
        {
            "title": "Prüfbedarf klären",
            "form": form,
            "text": (
                "Eine Klärung hebt keine Sperre auf und ändert keine Buchung. "
                "Tatsächliche Maßnahmen vorher durchführen und im Grund "
                "dokumentieren."
            ),
        },
    )


@page
@require_http_methods(["GET"])
def hours_admin(request):
    from inventory.views import any_action

    if not any_action(request.user, "booking.configure"):
        raise PermissionDenied

    def permitted(row):
        return allowed(
            request.user,
            "booking.configure",
            services.schedule_scope(
                row.resource_id, row.location_id, row.category_id, row.organization
            ),
        )

    windows = [
        r
        for r in ScheduleWindow.objects.select_related("resource", "location", "category")
        if permitted(r)
    ]
    exceptions = [
        r
        for r in ScheduleException.objects.select_related("resource", "location", "category")
        if permitted(r)
    ]

    def owner(row):
        if row.organization:
            return "organization", "Organisation"
        if row.resource_id:
            return "resource:" + str(row.resource_id), row.resource.title
        if row.category_id:
            return "category:" + str(row.category_id), "Kategorie: " + row.category.name
        return "location:" + str(row.location_id), "Standort: " + row.location.name

    owners = dict(owner(r) for r in [*windows, *exceptions])
    selected = request.GET.get("owner", "")[:100]
    purpose = request.GET.get("purpose", "")[:10]
    if selected:
        windows = [r for r in windows if owner(r)[0] == selected]
        exceptions = [r for r in exceptions if owner(r)[0] == selected]
    if purpose:
        windows = [r for r in windows if r.purpose == purpose]
        exceptions = [r for r in exceptions if r.purpose == purpose]
    from urllib.parse import urlencode

    query = urlencode({"owner": selected, "purpose": purpose})
    return render(
        request,
        "bookings/hours.html",
        {
            "windows": Paginator(windows, 30).get_page(request.GET.get("weekpage")),
            "exceptions": Paginator(exceptions, 30).get_page(request.GET.get("exceptionpage")),
            "owners": sorted(owners.items(), key=lambda pair: pair[1]),
            "purposes": ScheduleWindow._meta.get_field("purpose").choices,
            "selected_owner": selected,
            "selected_purpose": purpose,
            "filter_query": query,
        },
    )
