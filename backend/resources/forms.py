from django import forms
from inventory.forms import NodeChoice, permitted_nodes
from inventory.models import Category, Location
from inventory.services import visible_assets

from .models import Resource, ResourceType, ResourceUnit
from .services import resource_scope


class ResourceForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)

    class Meta:
        model = Resource
        fields = [
            "title",
            "slug",
            "type",
            "summary",
            "description",
            "location",
            "location_label",
            "catalog_area",
            "categories",
            "tags",
            "specifications",
            "safety_notes",
            "pickup_notes",
            "visibility",
            "booking_enabled",
            "is_featured",
        ]
        labels = {
            "title": "Titel",
            "slug": "Dauerhafter URL-Name",
            "type": "Art",
            "summary": "Kurzbeschreibung",
            "description": "Beschreibung",
            "location": "Interner Standort",
            "location_label": "Öffentliche Ortsangabe",
            "catalog_area": "Katalogbereich (optional)",
            "categories": "Kategorien",
            "tags": "Schlagworte",
            "specifications": "Ausstattung und technische Angaben",
            "safety_notes": "Sicherheitshinweise",
            "pickup_notes": "Abhol- und Nutzungshinweise",
            "visibility": "Sichtbarkeit nach Veröffentlichung",
            "booking_enabled": "Reservierung erlauben",
            "is_featured": "Auf der Startseite hervorheben",
        }
        widgets = {
            k: forms.Textarea(attrs={"rows": 4})
            for k in ("description", "specifications", "safety_notes", "pickup_notes")
        }

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"] = NodeChoice(
            label="Interner Standort", queryset=permitted_nodes(actor, Location, "location.read")
        )
        self.fields["categories"].queryset = permitted_nodes(actor, Category, "category.read")
        self.fields["type"].queryset = ResourceType.objects.filter(is_active=True)
        self.fields[
            "location_label"
        ].help_text = "Nur dieser Text erscheint im Katalog, nicht der interne Standortpfad."
        if not self.instance._state.adding:
            self.fields.pop("slug")
            self.fields["revision"].initial = self.instance.revision


class UnitForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)

    class Meta:
        model = ResourceUnit
        fields = ["name", "public_name", "asset", "is_active"]
        labels = {
            "name": "Interne Bezeichnung des Exemplars",
            "public_name": "Name für die Buchungsauswahl (optional)",
            "asset": "Inventargegenstand (optional)",
            "is_active": "Aktiv",
        }

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["asset"].queryset = visible_assets(actor).filter(
            archived_at__isnull=True, resource_unit__isnull=True
        )
        self.fields["asset"].help_text = (
            "Leer lassen für eine logische Einheit, etwa einen Raum. "
            "Die Zuordnung bleibt dauerhaft."
        )
        if not self.instance._state.adding:
            self.fields.pop("asset")
            self.fields["revision"].initial = self.instance.revision


class PoolForm(forms.Form):
    public_name = forms.CharField(
        label="Name für die Buchungsauswahl (optional)", max_length=120, required=False
    )
    name = forms.CharField(label="Poolname", max_length=120)
    units = forms.ModelMultipleChoiceField(
        label="Äquivalente Einheiten", required=False, queryset=ResourceUnit.objects.none()
    )
    is_active = forms.BooleanField(label="Aktiv", required=False, initial=True)
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)

    def __init__(self, resource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["units"].queryset = resource.units.filter(is_active=True)


class PublicationForm(forms.Form):
    operation = forms.ChoiceField(
        label="Aktion",
        choices=[
            ("publish", "Veröffentlichen"),
            ("withdraw", "Zurückziehen"),
            ("archive", "Archivieren"),
        ],
    )
    reason = forms.CharField(label="Grund", max_length=500)
    revision = forms.IntegerField(widget=forms.HiddenInput)


class ImageForm(forms.Form):
    file = forms.FileField(label="Katalogbild (PNG/JPEG, maximal 5 MiB)")
    alt_text = forms.CharField(label="Beschreibender Alternativtext", max_length=200)


class TypeForm(forms.ModelForm):
    class Meta:
        model = ResourceType
        fields = ["key", "name"]
        labels = {"key": "Typenschlüssel", "name": "Anzeigename"}


class RequirementsForm(forms.Form):
    agreements = forms.ModelMultipleChoiceField(
        label="Erforderliche Vereinbarungen",
        queryset=Category.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    qualifications = forms.ModelMultipleChoiceField(
        label="Erforderliche Einweisungen",
        queryset=Category.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, resource=None, **kwargs):
        super().__init__(*args, **kwargs)
        from lending.models import Agreement

        from .models import QualificationType

        self.fields["agreements"].queryset = Agreement.objects.filter(
            kind="additional", is_active=True
        )
        from .requirements import applies

        rows = QualificationType.objects.filter(is_active=True)
        self.fields["qualifications"].queryset = rows.filter(
            pk__in=[q.pk for q in rows if resource is None or applies(q, resource)]
        )


class QualificationForm(forms.Form):
    resource = forms.ModelChoiceField(
        label="Angebot (optional)", queryset=Resource.objects.none(), required=False
    )
    category = forms.ModelChoiceField(
        label="Kategorie (alternativ)", queryset=Category.objects.none(), required=False
    )

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.authorization import allowed
        from inventory.services import tree_scope

        self.fields["resource"].queryset = Resource.objects.filter(
            pk__in=[
                r.pk
                for r in Resource.objects.all()
                if allowed(actor, "booking.configure", resource_scope(r))
            ]
        )
        self.fields["category"].queryset = Category.objects.filter(
            pk__in=[
                c.pk
                for c in Category.objects.filter(is_active=True)
                if allowed(actor, "booking.configure", tree_scope(c))
            ]
        )

    name = forms.CharField(label="Name", max_length=120)
    description = forms.CharField(
        label="Beschreibung", max_length=2000, required=False, widget=forms.Textarea
    )


class IssueQualificationForm(forms.Form):
    user = forms.ModelChoiceField(label="Person", queryset=Category.objects.none())
    qualification = forms.ModelChoiceField(label="Einweisung", queryset=Category.objects.none())
    note = forms.CharField(label="Notiz (optional)", max_length=500, required=False)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User

        self.fields["user"].queryset = User.objects.filter(
            is_active=True, email_verified_at__isnull=False
        )
        from .requirements import visible_types

        self.fields["qualification"].queryset = visible_types(actor).filter(is_active=True)


class BundleForm(forms.Form):
    required_components = forms.ModelMultipleChoiceField(
        label="Erforderliche Angebote", queryset=Resource.objects.none(), required=False
    )
    optional_components = forms.ModelMultipleChoiceField(
        label="Optional wählbare Angebote", queryset=Resource.objects.none(), required=False
    )
    revision = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, actor, resource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.authorization import allowed

        rows = Resource.objects.filter(archived_at__isnull=True).exclude(pk=resource.pk)
        ids = [r.pk for r in rows if allowed(actor, "booking.configure", resource_scope(r))]
        for key in ("required_components", "optional_components"):
            self.fields[key].queryset = Resource.objects.filter(pk__in=ids)


class CategoryRequirementsForm(forms.Form):
    qualifications = forms.ModelMultipleChoiceField(
        label="Erforderliche Einweisungen einschließlich Unterkategorien",
        queryset=Category.objects.none(),
        required=False,
    )

    def __init__(self, category, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        from inventory.services import tree_scope

        from .models import QualificationType

        self.fields["qualifications"].queryset = QualificationType.objects.filter(
            is_active=True, resource__isnull=True
        ).filter(
            Q(category__isnull=True)
            | Q(category_id__in=[category.pk, *tree_scope(category).ancestors])
        )
