"""Resource requirements reuse lending agreements; qualifications never self-certify."""

from accounts.authorization import ORGANIZATION, allowed_many, authorization_write, require
from accounts.models import User
from accounts.services import audit
from django.core.exceptions import ValidationError
from lending.models import Acceptance, Agreement, AgreementAssignment

from resources.services import editable, resource_scope, visible_resources

from .models import (
    CategoryQualification,
    QualificationType,
    Resource,
    ResourceQualification,
    UserQualification,
)


def qualification_scope(qualification):
    if qualification.resource_id:
        return resource_scope(qualification.resource)
    if qualification.category_id:
        from inventory.services import tree_scope

        return tree_scope(qualification.category)
    return ORGANIZATION


def applies(qualification, resource):
    if qualification.resource_id:
        return qualification.resource_id == resource.pk
    if qualification.category_id:
        scope = resource_scope(resource)
        return any(
            c.kind == "category"
            and (c.id == qualification.category_id or qualification.category_id in c.ancestors)
            for c in scope.related
        )
    return True


def required_qualifications(resource):
    from uuid import UUID

    from django.db.models import Q

    categories: set[UUID] = set()
    for scope in resource_scope(resource).related:
        if scope.kind == "category":
            categories.update((scope.id, *scope.ancestors))
    return QualificationType.objects.filter(
        Q(resourcequalification__resource=resource)
        | Q(categoryqualification__category_id__in=categories)
    ).distinct()


def visible_types(actor, action="qualification.issue"):
    rows = list(QualificationType.objects.select_related("resource__location", "category"))
    decisions = allowed_many(actor, action, [qualification_scope(q) for q in rows])
    return QualificationType.objects.filter(
        pk__in=[q.pk for q, ok in zip(rows, decisions, strict=True) if ok]
    )


def configure_category(actor, category_id, qualification_ids):
    from inventory.models import Category
    from inventory.services import tree_scope

    with authorization_write():
        category = Category.objects.get(pk=category_id, is_active=True)
        require(actor, "booking.configure", tree_scope(category))
        rows = list(QualificationType.objects.filter(pk__in=qualification_ids, is_active=True))
        if len(rows) != len(set(qualification_ids)) or any(
            q.resource_id
            or (
                q.category_id
                and q.category_id not in (category.pk, *tree_scope(category).ancestors)
            )
            for q in rows
        ):
            raise ValidationError("Einweisungen müssen für diesen Kategoriebereich gelten.")
        CategoryQualification.objects.filter(category=category).exclude(
            qualification__in=rows
        ).delete()
        for row in rows:
            CategoryQualification.objects.get_or_create(category=category, qualification=row)
        audit(
            actor,
            "category.qualifications_configured",
            object_id=category.pk,
            details={"qualifications": [str(q.pk) for q in rows]},
        )


def required_agreements(resource):
    from lending.agreements import required_versions

    if hasattr(resource, "bookingpolicy") and resource.bookingpolicy.use_mode == "physical_loan":
        return required_versions(resource)
    agreements = Agreement.objects.filter(
        agreementassignment__resource=resource, is_active=True
    ).distinct()
    versions = []
    for agreement in agreements:
        version = agreement.versions.filter(published_at__isnull=False).order_by("-number").first()
        if version is None:
            raise ValidationError("agreement_required")
        versions.append(version)
    return versions


def outstanding(user, resource):
    versions = required_agreements(resource)
    accepted = set(
        Acceptance.objects.filter(user=user, version__in=versions).values_list(
            "version_id", flat=True
        )
    )
    qualifications = list(required_qualifications(resource))
    held = set(
        UserQualification.objects.filter(user=user).values_list("qualification_id", flat=True)
    )
    return [v for v in versions if v.pk not in accepted], [
        q for q in qualifications if q.pk not in held or not q.is_active or not applies(q, resource)
    ]


def gate(user, resource):
    missing, qualifications = outstanding(user, resource)
    policy = resource.bookingpolicy
    if qualifications or (
        policy.requires_qualification and not required_qualifications(resource).exists()
    ):
        return "qualification_required"
    if missing or (policy.requires_agreement and not required_agreements(resource)):
        return "agreement_required"
    return None


def configure(actor, resource_id, agreement_ids, qualification_ids):
    with authorization_write():
        resource = Resource.objects.get(pk=resource_id)
        editable(resource)
        require(actor, "booking.configure", resource_scope(resource))
        require(actor, "agreement.assign", resource_scope(resource))
        agreements = list(
            Agreement.objects.filter(pk__in=agreement_ids, kind="additional", is_active=True)
        )
        qualifications = list(
            QualificationType.objects.filter(pk__in=qualification_ids, is_active=True)
        )
        if any(not applies(q, resource) for q in qualifications):
            raise ValidationError("Einweisung gilt nicht für dieses Angebot.")
        if len(agreements) != len(set(agreement_ids)) or len(qualifications) != len(
            set(qualification_ids)
        ):
            raise ValidationError("Aktuelle Vereinbarungen und Einweisungen auswählen.")
        # Remove only resource mappings, never published texts, acceptance or issuance history.
        AgreementAssignment.objects.filter(resource=resource).exclude(
            agreement__in=agreements
        ).delete()
        for agreement in agreements:
            AgreementAssignment.objects.get_or_create(resource=resource, agreement=agreement)
        ResourceQualification.objects.filter(resource=resource).exclude(
            qualification__in=qualifications
        ).delete()
        for qualification in qualifications:
            ResourceQualification.objects.get_or_create(
                resource=resource, qualification=qualification
            )
        if hasattr(resource, "bookingpolicy"):
            from bookings.services import save_policy

            save_policy(
                actor,
                resource.pk,
                {
                    "requires_qualification": bool(qualifications),
                    "requires_agreement": bool(agreements),
                },
                resource.bookingpolicy.revision,
            )
        audit(
            actor,
            "resource.requirements_configured",
            object_id=resource.pk,
            details={
                "agreements": [str(a.pk) for a in agreements],
                "qualifications": [str(q.pk) for q in qualifications],
            },
        )


def create_type(actor, name, description="", *, resource=None, category=None):
    with authorization_write():
        if resource and category:
            raise ValidationError("Genau einen Einweisungsbereich wählen.")
        row = QualificationType(
            name=name, description=description, resource=resource, category=category
        )
        # Global creation retains the existing organization-level issuer gate.
        require(
            actor,
            "booking.configure" if resource or category else "qualification.issue",
            qualification_scope(row),
        )
        row.full_clean()
        row.save()
        audit(actor, "qualification.type_created", object_id=row.pk)
        return row


def issue(actor, user_id, qualification_id, note=""):
    with authorization_write():
        qualification = QualificationType.objects.get(pk=qualification_id, is_active=True)
        require(actor, "qualification.issue", qualification_scope(qualification))
        user = User.objects.get(pk=user_id, is_active=True, email_verified_at__isnull=False)
        row, created = UserQualification.objects.get_or_create(
            user=user, qualification=qualification, defaults={"issued_by": actor, "note": note}
        )
        if created:
            row.full_clean()
            audit(actor, "qualification.issued", subject=user, object_id=row.pk)
        return row


def account_status(user):
    statuses = []
    for resource in visible_resources(user):
        if not (
            required_qualifications(resource).exists()
            or AgreementAssignment.objects.filter(resource=resource).exists()
        ):
            continue
        try:
            versions = required_agreements(resource)
        except ValidationError:
            versions = []
        held = set(
            UserQualification.objects.filter(user=user).values_list("qualification_id", flat=True)
        )
        accepted = set(Acceptance.objects.filter(user=user).values_list("version_id", flat=True))
        statuses.append(
            {
                "resource": resource,
                "agreements": [(v, v.pk in accepted) for v in versions],
                "qualifications": [
                    (q, q.pk in held and q.is_active and applies(q, resource))
                    for q in required_qualifications(resource)
                ],
            }
        )
    return statuses
