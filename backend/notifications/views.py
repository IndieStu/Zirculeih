import calendar
from datetime import date, datetime, time, timedelta

from accounts.authorization import authorization_write, require
from accounts.ratelimit import take
from accounts.views import throttled
from bookings.views import page
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import calendars, forms, services
from .models import CalendarFeed, Delivery, NotificationPreference, NotificationTemplate


@page
@require_http_methods(["GET", "POST"])
def feeds(request):
    form = forms.FeedForm(request.user, request.POST or None)
    raw_url = None
    if request.method == "POST":
        if not take(request, "calendar-management", str(request.user.pk), limit=60):
            return throttled()
        try:
            action = request.POST.get("action")
            if action == "revoke":
                calendars.revoke(request.user, request.POST.get("feed_id"))
                return redirect("calendar_feeds")
            if action == "regenerate":
                _, raw = calendars.regenerate(request.user, request.POST.get("feed_id"))
                raw_url = services.absolute("/kalender/abo/" + raw + ".ics")
                form = forms.FeedForm(request.user)
            elif action == "create" and form.is_valid():
                data = form.cleaned_data
                _, raw = calendars.create(
                    request.user, data["label"], data["scope"], data["scope_id"], days=data["days"]
                )
                raw_url = services.absolute("/kalender/abo/" + raw + ".ics")
                form = forms.FeedForm(request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "notifications/feeds.html",
        dict(
            form=form,
            raw_url=raw_url,
            feeds=Paginator(
                CalendarFeed.objects.filter(owner=request.user).order_by("-created_at"), 30
            ).get_page(request.GET.get("page")),
        ),
    )


@require_http_methods(["GET", "HEAD"])
def subscription(request, raw):
    try:
        if not take(request, "calendar-fetch", hashlib_digest(raw), limit=240):
            return throttled()
        content = calendars.fetch(raw)
    except (PermissionDenied, ObjectDoesNotExist, ValidationError, ValueError):
        response = HttpResponse(status=404)
    else:
        response = HttpResponse(
            content if request.method != "HEAD" else b"",
            content_type="text/calendar; charset=utf-8",
        )
        response["Content-Disposition"] = 'inline; filename="deelvo.ics"'
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def hashlib_digest(raw):
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()


@page
@require_http_methods(["GET", "POST"])
def preferences(request):
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        with authorization_write():
            pref.qualification_email = request.POST.get("qualification_email") == "on"
            locale = request.POST.get("locale", "de")
            if locale not in {"de", "en"}:
                raise Http404
            pref.locale = locale
            pref.save()
        return redirect("notification_preferences")
    return render(request, "notifications/preferences.html", dict(preference=pref))


@page
@require_http_methods(["GET", "POST"])
def administration(request):
    require(request.user, "system.configure")
    config = services.configuration()
    settings_form = forms.SettingsForm(instance=config)
    template = NotificationTemplate.objects.filter(
        kind=request.GET.get("kind", "booking.confirmed"), locale=request.GET.get("locale", "de")
    ).first()
    initial = dict(
        kind=request.GET.get("kind", "booking.confirmed"),
        locale=request.GET.get("locale", "de"),
        subject=template.subject
        if template
        else "Deelvo · " + services.TITLES.get(request.GET.get("kind"), "Reservierung bestätigt"),
        body=template.body if template else "Details: ${url}\n${when}",
        revision=template.revision if template else None,
    )
    template_form = forms.TemplateForm(initial=initial)
    error = None
    if request.method == "POST":
        try:
            action = request.POST.get("action")
            if action == "settings":
                settings_form = forms.SettingsForm(request.POST, instance=config)
                if settings_form.is_valid():
                    services.save_settings(request.user, settings_form.cleaned_data)
                    return redirect("notification_admin")
            elif action == "template":
                template_form = forms.TemplateForm(request.POST)
                if template_form.is_valid():
                    services.save_template(request.user, **template_form.cleaned_data)
                    return redirect("notification_admin")
            elif action == "retry":
                services.retry(request.user, request.POST.get("delivery_id"))
                return redirect("notification_admin")
        except ValidationError as exc:
            error = " ".join(exc.messages)
    rows = Delivery.objects.select_related("user").order_by("-created_at")
    return render(
        request,
        "notifications/admin.html",
        dict(
            error=error,
            settings_form=settings_form,
            template_form=template_form,
            page_obj=Paginator(rows, 30).get_page(request.GET.get("page")),
        ),
    )


@page
@require_http_methods(["GET"])
def month(request):
    chooser = forms.FeedForm(
        request.user,
        initial={"scope": "personal", "label": "Kalender", "days": 90},
    )
    scope, scope_id = "personal", None
    if request.GET.get("scope"):
        bound = request.GET.copy()
        bound.update(label="Kalender", days="90")
        chooser = forms.FeedForm(request.user, bound)
        if not chooser.is_valid():
            raise Http404
        scope, scope_id = chooser.cleaned_data["scope"], chooser.cleaned_data["scope_id"]
    try:
        selected = date.fromisoformat(request.GET.get("day", timezone.localdate().isoformat()))
    except ValueError:
        raise Http404 from None
    first = selected.replace(day=1)
    if not 1971 <= first.year <= 9998:
        raise Http404
    days = list(calendar.Calendar().itermonthdates(first.year, first.month))
    tz = timezone.get_current_timezone()
    start = datetime.combine(days[0], time(), tzinfo=tz)
    end = datetime.combine(days[-1] + timedelta(days=1), time(), tzinfo=tz)
    events = calendars.logical_events(request.user, scope, scope_id, start=start, end=end)
    cells = []
    for day in days:
        members = [
            b
            for _, b in events
            if b.start.astimezone(tz).date()
            <= day
            <= (b.end - timedelta(microseconds=1)).astimezone(tz).date()
            and b.status not in {"cancelled", "no_show"}
        ]
        cells.append(dict(day=day, bookings=members, selected=day == selected))
    selected_rows = next(cell["bookings"] for cell in cells if cell["day"] == selected)
    from urllib.parse import urlencode

    filters = {
        k: request.GET[k] for k in ("scope", "resource", "category", "location") if k in request.GET
    }
    return render(
        request,
        "notifications/calendar.html",
        dict(
            display_timezone=timezone.get_current_timezone_name(),
            weekday_names=["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
            cells=cells,
            day=selected,
            month=first,
            selected_rows=selected_rows,
            chooser=chooser,
            previous="?" + urlencode({**filters, "day": (first - timedelta(days=1)).isoformat()}),
            following="?"
            + urlencode(
                {**filters, "day": (first + timedelta(days=32)).replace(day=1).isoformat()}
            ),
            suffix="&" + urlencode(filters),
        ),
    )
