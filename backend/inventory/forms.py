from accounts.authorization import allowed
from django import forms

from .models import (
    Asset,
    Category,
    CustomFieldDefinition,
    Identifier,
    IdentifierNamespace,
    Location,
)
from .services import asset_scope, tree_scope


class NodeChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.breadcrumb


def permitted_nodes(actor, model, action):
    return model.objects.filter(
        pk__in=[n.pk for n in model.objects.all() if allowed(actor, action, tree_scope(n))]
    )


class AssetForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)

    class Meta:
        model = Asset
        fields = [
            "inventory_number",
            "name",
            "description",
            "category",
            "location",
            "tags",
            "manufacturer",
            "model",
            "serial_number",
            "acquisition_date",
            "acquisition_value",
            "condition",
            "lifecycle",
            "internal_notes",
        ]
        labels = {
            "inventory_number": "Inventarnummer",
            "name": "Name",
            "description": "Beschreibung",
            "category": "Kategorie",
            "location": "Standort",
            "tags": "Schlagworte",
            "manufacturer": "Hersteller",
            "model": "Modell",
            "serial_number": "Seriennummer",
            "acquisition_date": "Anschaffungsdatum",
            "acquisition_value": "Anschaffungswert",
            "condition": "Zustand",
            "lifecycle": "Lebenszyklus",
            "internal_notes": "Interne Notizen",
        }
        widgets = {
            "acquisition_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "internal_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"] = NodeChoice(
            label="Standort", queryset=permitted_nodes(actor, Location, "location.read")
        )
        self.fields["category"] = NodeChoice(
            label="Kategorie", queryset=permitted_nodes(actor, Category, "category.read")
        )
        if self.instance.pk and not self.instance._state.adding:
            scope = asset_scope(self.instance)
            self.fields.pop("inventory_number")
            self.fields.pop("location")
            self.fields["revision"].initial = self.instance.revision
        else:
            from accounts.authorization import Scope

            scope = Scope()
            self.fields["revision"].initial = 0
        # Scoped sensitive writes are admitted against the currently selected server-side targets.
        if self.is_bound and "location" in self.fields:
            try:
                location = Location.objects.get(pk=self.data.get("location"))
                category = Category.objects.get(pk=self.data.get("category"))
                scope = asset_scope(Asset(location=location, category=category))
            except (
                Location.DoesNotExist,
                Category.DoesNotExist,
                forms.ValidationError,
                ValueError,
            ):
                pass
        if not allowed(actor, "asset.read_sensitive", scope):
            self.fields.pop("serial_number")
            self.fields.pop("internal_notes")
        if not allowed(actor, "asset.read_financial", scope):
            self.fields.pop("acquisition_value")


class LocationForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Location
        fields = ["name", "description", "parent", "is_active"]
        labels = {
            "name": "Name",
            "description": "Beschreibung",
            "parent": "Übergeordneter Ort",
            "is_active": "Aktiv",
        }


class CategoryForm(forms.ModelForm):
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Category
        fields = ["name", "description", "parent", "is_active"]
        labels = {
            "name": "Name",
            "description": "Beschreibung",
            "parent": "Übergeordnete Kategorie",
            "is_active": "Aktiv",
        }


class LookupForm(forms.Form):
    namespace = forms.ModelChoiceField(
        label="Code-Namensraum", queryset=IdentifierNamespace.objects.filter(is_active=True)
    )
    code = forms.CharField(
        label="Code scannen oder eingeben",
        max_length=256,
        strip=False,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "off"}),
    )


class IdentifierForm(forms.Form):
    namespace = forms.ModelChoiceField(
        label="Code-Namensraum",
        queryset=IdentifierNamespace.objects.filter(is_active=True).exclude(
            key__in=["deelvo", "inventory"]
        ),
    )
    raw = forms.CharField(label="Code", max_length=128, strip=False)
    kind = forms.ChoiceField(
        label="Art",
        choices=[c for c in Identifier.Kind.choices if c[0] not in {"owned", "inventory"}],
    )
    source = forms.CharField(label="Herkunft", max_length=200, required=False)


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Grund", max_length=500)
    revision = forms.IntegerField(widget=forms.HiddenInput)


class MoveForm(ReasonForm):
    location = NodeChoice(label="Neuer Standort", queryset=Location.objects.filter(is_active=True))


class NamespaceForm(forms.ModelForm):
    class Meta:
        model = IdentifierNamespace
        fields = ["key", "name", "normalization"]
        labels = {"key": "Namensraumschlüssel", "name": "Name", "normalization": "Vergleichsregel"}


class FieldDefinitionForm(forms.ModelForm):
    option_lines = forms.CharField(
        label="Auswahlwerte (ein Wert pro Zeile)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = CustomFieldDefinition
        fields = ["key", "label", "kind", "is_sensitive"]
        labels = {
            "key": "Feldschlüssel",
            "label": "Bezeichnung",
            "kind": "Datentyp",
            "is_sensitive": "Vertrauliches Zusatzfeld",
        }


class CustomValueForm(forms.Form):
    definition = forms.ModelChoiceField(
        label="Zusatzfeld", queryset=CustomFieldDefinition.objects.filter(is_active=True)
    )
    value = forms.CharField(label="Wert (Datum JJJJ-MM-TT; Ja/Nein: true/false)", max_length=2000)
    revision = forms.IntegerField(widget=forms.HiddenInput)


class UploadForm(forms.Form):
    file = forms.FileField(label="PNG/JPEG-Bild oder UTF-8-Textdokument")
    is_sensitive = forms.BooleanField(
        label="Nur mit Recht für vertrauliche Inventardaten sichtbar", initial=True, required=False
    )


class CSVForm(forms.Form):
    file = forms.FileField(label="CSV-Datei (UTF-8; maximal 200 Zeilen)")


class TagForm(forms.Form):
    name = forms.CharField(label="Neues Schlagwort", max_length=80)
