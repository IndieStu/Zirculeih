"""Resource requirements reuse lending agreements; qualifications never self-certify."""

from accounts.authorization import authorization_write, require
from accounts.models import User
from accounts.services import audit
from django.core.exceptions import ValidationError
from lending.models import Acceptance, Agreement, AgreementAssignment

from resources.services import editable, resource_scope, visible_resources

from .models import QualificationType, Resource, ResourceQualification, UserQualification


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
    qualifications = list(
        QualificationType.objects.filter(resourcequalification__resource=resource)
    )
    held = set(
        UserQualification.objects.filter(user=user).values_list("qualification_id", flat=True)
    )
    return [v for v in versions if v.pk not in accepted], [
        q for q in qualifications if q.pk not in held or not q.is_active
    ]


def gate(user, resource):
    missing, qualifications = outstanding(user, resource)
    policy = resource.bookingpolicy
    if qualifications or (policy.requires_qualification and not resource.qualifications.exists()):
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
        audit(
            actor,
            "resource.requirements_configured",
            object_id=resource.pk,
            details={
                "agreements": [str(a.pk) for a in agreements],
                "qualifications": [str(q.pk) for q in qualifications],
            },
        )


def create_type(actor, name, description=""):
    with authorization_write():
        require(actor, "qualification.issue")
        row = QualificationType(name=name, description=description)
        row.full_clean()
        row.save()
        audit(actor, "qualification.type_created", object_id=row.pk)
        return row


def issue(actor, user_id, qualification_id, note=""):
    with authorization_write():
        require(actor, "qualification.issue")
        user = User.objects.get(pk=user_id, is_active=True, email_verified_at__isnull=False)
        qualification = QualificationType.objects.get(pk=qualification_id, is_active=True)
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
            resource.qualifications.exists()
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
                    (r.qualification, r.qualification_id in held and r.qualification.is_active)
                    for r in resource.qualifications.select_related("qualification")
                ],
            }
        )
    return statuses
