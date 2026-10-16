from functools import wraps

from accounts.authorization import allowed, require
from accounts.ratelimit import take
from accounts.views import throttled
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from inventory import extensions
from inventory.forms import IdentifierForm, ReasonForm
from inventory.models import Category, Identifier, IdentifierNamespace
from inventory.services import descendants

from . import forms, services
from .models import Resource, ResourceImage, ResourcePool, ResourceType, ResourceUnit


def operation(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except (
            Resource.DoesNotExist,
            ResourceUnit.DoesNotExist,
            ResourcePool.DoesNotExist,
            ResourceImage.DoesNotExist,
            Identifier.DoesNotExist,
            IdentifierNamespace.DoesNotExist,
            PermissionDenied,
            FileNotFoundError,
        ) as exc:
            raise Http404 from exc

    return wrapped


def form_result(request, form, title, save, resource=None, multipart=False):
    if request.method == "POST" and form.is_valid():
        try:
            result = save(dict(form.cleaned_data))
            messages.success(request, "Gespeichert.")
            return redirect("resource_manage", resource_id=resource.pk if resource else result.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request, "resources/form.html", {"form": form, "title": title, "multipart": multipart}
    )


def catalog_query(request):
    qs = services.visible_resources(request.user)
    query = request.GET.get("q", "")[:200].strip()
    if query:
        from django.db.models import Q

        qs = qs.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(specifications__icontains=query)
        )
    for field, model in (("category", Category),):
        if request.GET.get(field):
            try:
                node = model.objects.get(pk=request.GET[field])
                key = "categories__id__in" if field == "category" else "location_id__in"
                qs = qs.filter(**{key: descendants(model, node.pk)})
            except (ValidationError, ValueError, model.DoesNotExist):
                qs = qs.none()
    if request.GET.get("area"):
        qs = qs.filter(catalog_area=request.GET["area"][:100])
    if request.GET.get("type"):
        try:
            qs = qs.filter(type_id=request.GET["type"])
        except (ValidationError, ValueError):
            qs = qs.none()
    return qs.distinct()


@require_http_methods(["GET"])
def catalog(request):
    visible = services.visible_resources(request.user)
    page = Paginator(catalog_query(request), 24).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    # Filter labels derive solely from visible resources; never enumerate private inventory paths.
    areas = list(
        visible.exclude(catalog_area="")
        .values_list("catalog_area", flat=True)
        .distinct()
        .order_by("catalog_area")
    )
    return render(
        request,
        "resources/catalog.html",
        {
            "cards": [services.catalog_card(r) for r in page],
            "page_obj": page,
            "categories": Category.objects.filter(resource__in=visible).distinct(),
            "types": ResourceType.objects.filter(resource__in=visible).distinct(),
            "areas": areas,
            "pagination_query": query.urlencode() + "&" if query else "",
        },
    )


@require_http_methods(["GET"])
def detail(request, slug):
    resource = get_object_or_404(services.visible_resources(request.user), slug=slug)
    from .calendar import calendar

    # Only explicitly authored catalog fields, never the inventory models or unit names.
    return render(
        request,
        "resources/detail.html",
        {
            "card": services.catalog_card(resource),
            "calendar": calendar(
                resource,
                request.GET.get("day"),
                month=request.GET.get("month"),
                actor=request.user,
                query=request.GET,
            ),
            "description": resource.description,
            "specifications": resource.specifications,
            "safety_notes": resource.safety_notes,
            "pickup_notes": resource.pickup_notes,
            "images": resource.images.filter(archived_at__isnull=True),
            "internal": resource.visibility == "private",
            "booking_ready": resource.booking_enabled and hasattr(resource, "bookingpolicy"),
        },
    )


@operation
@require_http_methods(["GET"])
def management(request):
    if not can_manage(request.user) and not allowed(request.user, "resource.type_manage"):
        raise PermissionDenied
    rows = services.visible_resources(request.user, management=True)
    return render(
        request,
        "resources/manage_list.html",
        {
            "resources": rows,
            "can_create": allowed(request.user, "resource.manage"),
            "can_types": allowed(request.user, "resource.type_manage"),
        },
    )


def can_manage(actor):
    from inventory.views import any_action

    return any_action(actor, "resource.manage")


@operation
@require_http_methods(["GET", "POST"])
def edit(request, resource_id=None):
    resource = services.read_resource(request.user, resource_id) if resource_id else None
    if resource and resource.published_at:
        require(request.user, "resource.publish", services.resource_scope(resource))
    if not can_manage(request.user):
        raise PermissionDenied
    form = forms.ResourceForm(request.user, request.POST or None, instance=resource)

    def save(data):
        revision = data.pop("revision")
        return services.save_resource(
            request.user, data, resource_id=resource_id, expected_revision=revision
        )

    return form_result(
        request, form, "Angebot bearbeiten" if resource else "Angebot anlegen", save, resource
    )


@operation
@require_http_methods(["GET"])
def manage_detail(request, resource_id):
    resource = services.read_resource(request.user, resource_id)
    pools = list(resource.pools.prefetch_related("memberships__unit"))
    for pool in pools:
        pool.eligible_count = services.eligible_pool_units(request.user, pool).count()
    return render(
        request,
        "resources/manage_detail.html",
        {
            "resource": resource,
            "units": resource.units.select_related("asset"),
            "pools": pools,
            "can_requirements": allowed(
                request.user, "booking.configure", services.resource_scope(resource)
            )
            and allowed(request.user, "agreement.assign", services.resource_scope(resource)),
            "can_hours": allowed(
                request.user, "booking.configure", services.resource_scope(resource)
            ),
            "can_publish": allowed(
                request.user, "resource.publish", services.resource_scope(resource)
            ),
            "can_codes": allowed(
                request.user, "identifier.assign", services.resource_scope(resource)
            ),
            "can_retire": allowed(
                request.user, "identifier.retire", services.resource_scope(resource)
            ),
            "images": resource.images.filter(archived_at__isnull=True),
        },
    )


@operation
@require_http_methods(["GET", "POST"])
def publish(request, resource_id):
    resource = services.read_resource(request.user, resource_id)
    require(request.user, "resource.publish", services.resource_scope(resource))
    form = forms.PublicationForm(request.POST or None, initial={"revision": resource.revision})
    return form_result(
        request,
        form,
        "Sichtbarkeit ausdrücklich ändern",
        lambda data: services.publication(
            request.user, resource.pk, data["revision"], data["operation"], data["reason"]
        ),
        resource,
    )


@operation
@require_http_methods(["GET", "POST"])
def unit_edit(request, resource_id, unit_id=None):
    resource = services.read_resource(request.user, resource_id)
    unit = get_object_or_404(ResourceUnit, pk=unit_id, resource=resource) if unit_id else None
    form = forms.UnitForm(request.user, request.POST or None, instance=unit)

    def save(data):
        revision = data.pop("revision")
        return services.save_unit(
            request.user, resource.pk, data, unit_id=unit_id, expected_revision=revision
        )

    return form_result(
        request, form, "Einheit bearbeiten" if unit else "Einheit hinzufügen", save, resource
    )


@operation
@require_http_methods(["GET", "POST"])
def pool_edit(request, resource_id, pool_id=None):
    resource = services.read_resource(request.user, resource_id)
    pool = get_object_or_404(ResourcePool, pk=pool_id, resource=resource) if pool_id else None
    initial = (
        {
            "revision": pool.revision,
            "name": pool.name,
            "is_active": pool.is_active,
            "units": pool.memberships.values_list("unit_id", flat=True),
        }
        if pool
        else {}
    )
    form = forms.PoolForm(resource, request.POST or None, initial=initial)

    def save(data):
        revision = data.pop("revision")
        return services.save_pool(
            request.user, resource.pk, **data, pool_id=pool_id, expected_revision=revision
        )

    return form_result(request, form, "Pool konfigurieren", save, resource)


@operation
@require_http_methods(["GET", "POST"])
def image_upload(request, resource_id):
    resource = services.read_resource(request.user, resource_id)
    if resource.published_at:
        require(request.user, "resource.publish", services.resource_scope(resource))
    if request.method == "POST" and not take(
        request, "resource-upload", str(request.user.pk), limit=20
    ):
        return throttled()
    form = forms.ImageForm(request.POST or None, request.FILES or None)
    return form_result(
        request,
        form,
        "Katalogbild hinzufügen",
        lambda data: services.upload_image(
            request.user, resource.pk, data["file"], data["alt_text"]
        ),
        resource,
        multipart=True,
    )


@require_http_methods(["GET"])
def image(request, image_id):
    row = get_object_or_404(ResourceImage, pk=image_id, archived_at__isnull=True)
    visible = services.visible_resources(request.user).filter(pk=row.resource_id).exists()
    if not visible and not allowed(
        request.user, "resource.manage", services.resource_scope(row.resource)
    ):
        raise Http404
    try:
        response = FileResponse(
            extensions.media_storage().open(row.storage_name, "rb"), content_type="image/jpeg"
        )
    except FileNotFoundError as exc:
        raise Http404 from exc
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


@operation
@require_POST
def image_archive(request, image_id):
    row = ResourceImage.objects.get(pk=image_id)
    services.archive_image(request.user, row.pk)
    return redirect("resource_manage", resource_id=row.resource_id)


@operation
@require_http_methods(["GET", "POST"])
def type_create(request, type_id=None):
    require(request.user, "resource.type_manage")
    row = get_object_or_404(ResourceType, pk=type_id) if type_id else None
    form = forms.TypeForm(request.POST or None, instance=row)
    if request.method == "POST" and form.is_valid():
        try:
            services.save_type(request.user, form.cleaned_data, type_id=type_id)
            return redirect("resource_types")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "resources/form.html",
        {
            "title": "Art bearbeiten" if row else "Art anlegen",
            "form": form,
            "types": ResourceType.objects.all(),
        },
    )


@operation
@require_http_methods(["GET", "POST"])
def unit_code(request, resource_id, unit_id, identifier_id=None):
    resource = services.read_resource(request.user, resource_id)
    unit = get_object_or_404(ResourceUnit, pk=unit_id, resource=resource)
    action = "identifier.retire" if identifier_id else "identifier.assign"
    require(request.user, action, services.resource_scope(resource))
    form = (
        ReasonForm(request.POST or None, initial={"revision": unit.revision})
        if identifier_id
        else IdentifierForm(request.POST or None)
    )

    def save(data):
        if identifier_id:
            return services.retire_unit_identifier(
                request.user, unit.pk, identifier_id, data["reason"]
            )
        return services.assign_unit_identifier(
            request.user, unit.pk, data["namespace"].pk, data["raw"], data["kind"], data["source"]
        )

    return form_result(
        request,
        form,
        "Einheitscode stilllegen" if identifier_id else "Einheitscode zuordnen",
        save,
        resource,
    )


@operation
@require_http_methods(["GET", "POST"])
def requirements_edit(request, resource_id):
    from lending.models import AgreementAssignment

    from . import requirements

    resource = get_object_or_404(Resource, pk=resource_id)
    require(request.user, "booking.configure", services.resource_scope(resource))
    require(request.user, "agreement.assign", services.resource_scope(resource))
    form = forms.RequirementsForm(
        request.POST or None,
        initial={
            "agreements": AgreementAssignment.objects.filter(resource=resource).values_list(
                "agreement_id", flat=True
            ),
            "qualifications": resource.qualifications.values_list("qualification_id", flat=True),
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            requirements.configure(
                request.user,
                resource.pk,
                [r.pk for r in form.cleaned_data["agreements"]],
                [r.pk for r in form.cleaned_data["qualifications"]],
            )
            messages.success(request, "Voraussetzungen gespeichert.")
            return redirect("resource_manage", resource_id=resource.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "resources/form.html",
        {"form": form, "title": resource.title + ": Voraussetzungen"},
    )


@operation
@require_http_methods(["GET", "POST"])
def qualifications_admin(request):
    from . import requirements
    from .models import QualificationType, UserQualification

    require(request.user, "qualification.issue")
    type_form = forms.QualificationForm(
        request.POST if request.POST.get("operation") == "type" else None
    )
    issue_form = forms.IssueQualificationForm(
        request.POST if request.POST.get("operation") == "issue" else None
    )
    if request.method == "POST":
        form = type_form if request.POST.get("operation") == "type" else issue_form
        if form.is_valid():
            try:
                data = form.cleaned_data
                if form is type_form:
                    requirements.create_type(request.user, data["name"], data["description"])
                else:
                    requirements.issue(
                        request.user, data["user"].pk, data["qualification"].pk, data["note"]
                    )
                messages.success(request, "Einweisung gespeichert.")
                return redirect("qualifications_admin")
            except ValidationError as exc:
                form.add_error(None, exc)
    return render(
        request,
        "resources/qualifications.html",
        {
            "type_form": type_form,
            "issue_form": issue_form,
            "types": QualificationType.objects.all(),
            "issuances": UserQualification.objects.select_related("user", "qualification").order_by(
                "-issued_at"
            )[:100],
        },
    )


@require_http_methods(["GET"])
def calendar_select(request, slug):
    from datetime import date, datetime, timedelta
    from urllib.parse import urlencode

    from bookings.models import BookingPolicy
    from bookings.occupancy import Occupancy
    from bookings.time_rules import interval

    from .calendar import validate_period

    resource = get_object_or_404(services.visible_resources(request.user), slug=slug)
    policy = get_object_or_404(BookingPolicy, resource=resource)
    error = None
    if not resource.booking_enabled:
        raise Http404
    try:
        parser = date.fromisoformat if policy.time_mode == "days" else datetime.fromisoformat
        start = parser(request.GET.get("start", ""))
        end = parser(request.GET.get("end", ""))
        sf = int(request.GET["start_fold"]) if request.GET.get("start_fold") else None
        ef = int(request.GET["end_fold"]) if request.GET.get("end_fold") else None
        s, e, _, _, _ = interval(policy, start, end, start_fold=sf, end_fold=ef)
        if e <= s or (e - s) > timedelta(days=367):
            raise ValueError
        snapshot = Occupancy(resource, policy, s, e, request.user)
        error = validate_period(snapshot, start, end, start_fold=sf, end_fold=ef)
        if error is None:
            params = {"start": start.isoformat(), "end": end.isoformat()}
            if sf is not None:
                params["start_fold"] = str(sf)
            if ef is not None:
                params["end_fold"] = str(ef)
            from django.urls import reverse

            return redirect(reverse("booking_create", args=[resource.pk]) + "?" + urlencode(params))
    except (ValueError, ValidationError, OverflowError) as exc:
        error = (
            exc.messages[0]
            if isinstance(exc, ValidationError)
            else "Bitte einen gültigen Zeitraum wählen."
        )
    return render(
        request, "resources/calendar_error.html", {"resource": resource, "error": error}, status=400
    )
