from accounts.authorization import allowed
from accounts.ratelimit import take
from accounts.views import throttled
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from inventory.views import any_action
from resources.services import resource_scope

from . import forms, recurrence
from .models import RequestOccurrence
from .views import error_message, page


@page
@require_http_methods(["GET"])
def queue(request):
    if not any_action(request.user, "booking.approve"):
        raise Http404
    rows = recurrence.visible(request.user, queue=True)
    return render(
        request,
        "bookings/requests.html",
        {"page_obj": Paginator(rows, 30).get_page(request.GET.get("page"))},
    )


@page
@require_http_methods(["GET", "POST"])
def detail(request, request_id):
    proposal = recurrence.read(request.user, request_id)
    form = forms.ReasonForm(request.POST or None, initial={"revision": proposal.revision})
    results = None
    preview_error = None
    from resources.models import Resource

    snapshot_resources = Resource.objects.filter(pk__in=proposal.resources_snapshot)
    can_approve = all(
        allowed(request.user, "booking.approve", resource_scope(r)) for r in snapshot_resources
    )
    if request.method == "POST":
        if not take(request, "request-decision", str(request.user.pk), limit=120):
            return throttled()
        action = request.POST.get("action")
        if action == "preview":
            form = forms.ReasonForm(initial={"revision": proposal.revision})
            try:
                results = recurrence.preview(request.user, proposal.pk)
            except ValidationError as exc:
                preview_error = error_message(exc)
        elif form.is_valid():
            try:
                if action in {"approve", "reject", "withdraw"}:
                    method = getattr(recurrence, action)
                    method(
                        request.user,
                        proposal.pk,
                        form.cleaned_data["revision"],
                        form.cleaned_data["reason"],
                    )
                    return redirect("request_detail", request_id=proposal.pk)
                else:
                    raise ValidationError("Unbekannte Aktion.")
            except recurrence.Conflicts as exc:
                results = exc.rows
                form.add_error(None, error_message(exc))
            except ValidationError as exc:
                form.add_error(None, error_message(exc))
    if results:
        from .views import MESSAGES

        for result in results:
            result["message"] = MESSAGES.get(result["code"], result["code"])
    rows = [
        {
            "occurrence": row,
            "booking": recurrence.current_booking(row),
            "adjustment": row.adjustments.last(),
        }
        for row in proposal.occurrences.all()
    ]
    return render(
        request,
        "bookings/request_detail.html",
        dict(
            proposal=proposal,
            rows=rows,
            form=form,
            results=results,
            can_approve=can_approve,
            preview_error=preview_error,
        ),
    )


@page
@require_http_methods(["GET", "POST"])
def exception(request, occurrence_id):
    row = RequestOccurrence.objects.select_related("request").get(pk=occurrence_id)
    proposal = recurrence.read(request.user, row.request_id)
    booking = recurrence.current_booking(row)
    pending = proposal.status == "requested"
    if not booking and not pending:
        raise Http404
    from .models import BookingPolicy

    policy = BookingPolicy.objects.get(resource=proposal.resource)
    reason = forms.ReasonForm(
        request.POST or None,
        initial={"revision": proposal.revision if pending else booking.revision},
    )
    effective = row.adjustments.last() or row
    start, end = recurrence._local(effective, proposal.time_mode)
    if booking:
        from datetime import timedelta

        from .time_rules import zone

        if booking.start_date:
            start, end = booking.start_date, booking.end_date_exclusive - timedelta(days=1)
        else:
            start = booking.start.astimezone(zone(booking.timezone)).replace(tzinfo=None)
            end = booking.end.astimezone(zone(booking.timezone)).replace(tzinfo=None)
    initial = {"start": start.isoformat(), "end": end.isoformat()}
    effective_options = recurrence._options(effective.options)
    for name in ("pickup_at", "return_at"):
        moment = effective_options.get(name)
        if moment:
            initial[name] = (
                moment.astimezone(recurrence.zone(proposal.timezone))
                .replace(tzinfo=None)
                .isoformat()
                if moment.tzinfo
                else moment.isoformat()
            )
    from resources.models import Resource

    needs_appointments = any(
        r.bookingpolicy.use_mode == "physical_loan"
        for r in Resource.objects.filter(pk__in=proposal.resources_snapshot)
    )
    times = forms.BookingForm(
        policy, request.POST or None, initial=initial, needs_appointments=needs_appointments
    )
    if request.method == "POST" and reason.is_valid():
        if not take(request, "request-exception", str(request.user.pk), limit=120):
            return throttled()
        try:
            data = reason.cleaned_data
            method = recurrence.adjust if pending else recurrence.exception
            if request.POST.get("action") == "cancel":
                method(request.user, row.pk, data["revision"], data["reason"])
            elif request.POST.get("action") == "move" and times.is_valid():
                options = {
                    k: v
                    for k, v in times.cleaned_data.items()
                    if k
                    in {"unit_id", "pool_id", "start_fold", "end_fold", "pickup_at", "return_at"}
                    and v is not None
                }
                method(
                    request.user,
                    row.pk,
                    data["revision"],
                    data["reason"],
                    start=times.cleaned_data["start"],
                    end=times.cleaned_data["end"],
                    **options,
                )
            else:
                raise ValidationError("Bitte die neuen Zeiten vollständig angeben.")
            return redirect("request_detail", request_id=proposal.pk)
        except ValidationError as exc:
            reason.add_error(None, error_message(exc))
    return render(
        request,
        "bookings/exception.html",
        dict(proposal=proposal, row=row, booking=booking, form=reason, times=times),
    )
