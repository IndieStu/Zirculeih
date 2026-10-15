from django import forms
from inventory.forms import NodeChoice, permitted_nodes
from inventory.models import Category, Location
from inventory.services import visible_assets

from .models import Resource, ResourceType, ResourceUnit


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
            "type": "Angebotstyp",
            "summary": "Kurzbeschreibung",
            "description": "Beschreibung",
            "location": "Interner Standort",
            "location_label": "Öffentliche Ortsangabe",
            "categories": "Kategorien",
            "tags": "Schlagworte",
            "specifications": "Ausstattung und technische Angaben",
            "safety_notes": "Sicherheitshinweise",
            "pickup_notes": "Abhol- und Nutzungshinweise",
            "visibility": "Sichtbarkeit nach Veröffentlichung",
            "booking_enabled": "Für spätere Buchung aktivieren (noch keine Buchungsfunktion)",
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
        fields = ["name", "asset", "is_active"]
        labels = {
            "name": "Interner Einheitsname",
            "asset": "Physisches Asset (optional)",
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
