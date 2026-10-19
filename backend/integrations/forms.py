from django import forms
from inventory.forms import permitted_nodes
from inventory.models import Category, Location
from inventory.services import visible_assets
from resources.services import visible_resources

from .models import IntegrationClient
from .services import CAPABILITIES


class ClientForm(forms.Form):
    name = forms.CharField(label="Name der Integration", max_length=100)
    capabilities = forms.MultipleChoiceField(
        label="Maximale Fähigkeiten",
        choices=[(key, value[0]) for key, value in CAPABILITIES.items()],
        widget=forms.CheckboxSelectMultiple,
    )
    scope_kind = forms.ChoiceField(
        label="Bereich",
        choices=[
            ("organization", "Gesamter aktuell erlaubter Bereich"),
            ("location", "Standort mit Unterorten"),
            ("category", "Kategorie mit Unterkategorien"),
            ("resource", "Ein Artikel / Raum"),
            ("asset", "Ein Inventargegenstand"),
        ],
    )
    location = forms.ModelChoiceField(
        label="Standort", queryset=Location.objects.none(), required=False
    )
    category = forms.ModelChoiceField(
        label="Kategorie", queryset=Category.objects.none(), required=False
    )
    resource = forms.ChoiceField(label="Artikel / Raum", choices=[], required=False)
    asset = forms.ChoiceField(label="Inventargegenstand", choices=[], required=False)
    password = forms.CharField(label="Lokales Passwort bestätigen", widget=forms.PasswordInput)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = permitted_nodes(actor, Location, "location.read")
        self.fields["category"].queryset = permitted_nodes(actor, Category, "category.read")
        self.fields["resource"].choices = [
            ("", "Bitte wählen"),
            *[(str(r.pk), r.title) for r in visible_resources(actor)],
        ]
        self.fields["asset"].choices = [
            ("", "Bitte wählen"),
            *[(str(a.pk), str(a)) for a in visible_assets(actor)[:2000]],
        ]

    def clean(self):
        data = super().clean()
        kind = data.get("scope_kind")
        value = data.get(kind) if kind in {"location", "category", "resource", "asset"} else None
        if kind != "organization" and not value:
            raise forms.ValidationError("Konkreten Bereich auswählen.")
        data["scope_id"] = getattr(value, "pk", value) or None
        return data


class TokenForm(forms.Form):
    client = forms.ModelChoiceField(label="Integration", queryset=IntegrationClient.objects.none())
    days = forms.IntegerField(label="Gültigkeit in Tagen", min_value=1, max_value=90, initial=30)
    read_only = forms.BooleanField(
        label="Nur lesen (keine Buchung, Ausgabe oder Änderung)", initial=True, required=False
    )
    password = forms.CharField(label="Lokales Passwort bestätigen", widget=forms.PasswordInput)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = IntegrationClient.objects.filter(
            owner=actor, retired_at=None
        )
