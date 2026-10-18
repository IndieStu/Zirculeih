from accounts.authorization import allowed
from django import forms
from inventory.forms import NodeChoice, permitted_nodes
from inventory.models import Category, Location
from resources.services import resource_scope, visible_resources

from .models import CalendarFeed, NotificationSettings
from .services import TITLES


class FeedForm(forms.Form):
    label = forms.CharField(label="Kalendername", max_length=100)
    scope = forms.ChoiceField(
        label="Bereich", choices=CalendarFeed._meta.get_field("scope").choices
    )
    resource = forms.ChoiceField(label="Artikel / Raum", required=False)
    category = NodeChoice(label="Kategorie", queryset=Category.objects.none(), required=False)
    location = NodeChoice(label="Standort", queryset=Location.objects.none(), required=False)
    days = forms.IntegerField(label="Gültigkeit in Tagen", min_value=1, max_value=366, initial=90)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rows = [
            r
            for r in visible_resources(actor)
            if allowed(actor, "booking.read_all", resource_scope(r))
        ]
        self.fields["resource"].choices = [
            ("", "Bitte wählen"),
            *[(str(r.pk), r.title) for r in rows],
        ]
        self.fields["category"].queryset = permitted_nodes(actor, Category, "booking.read_all")
        self.fields["location"].queryset = permitted_nodes(actor, Location, "booking.read_all")
        scopes = {"personal"}
        if rows:
            scopes.add("resource")
        if self.fields["category"].queryset.exists():
            scopes.add("category")
        if self.fields["location"].queryset.exists():
            scopes.add("location")
        if allowed(actor, "booking.read_all"):
            scopes.add("organization")
        self.fields["scope"].choices = [
            (value, label) for value, label in self.fields["scope"].choices if value in scopes
        ]

    def clean(self):
        data = super().clean()
        scope = data.get("scope")
        selected = data.get(scope) if scope in {"resource", "category", "location"} else None
        if scope in {"resource", "category", "location"} and not selected:
            raise forms.ValidationError("Den gewählten Bereich vollständig angeben.")
        data["scope_id"] = getattr(selected, "pk", selected)
        return data


class TemplateForm(forms.Form):
    kind = forms.ChoiceField(label="Nachricht", choices=[(k, v) for k, v in TITLES.items()])
    locale = forms.ChoiceField(label="Sprache", choices=[("de", "Deutsch"), ("en", "English")])
    subject = forms.CharField(label="Betreff", max_length=200)
    body = forms.CharField(
        label="Text (${url} und ${when})", widget=forms.Textarea, max_length=10000
    )
    revision = forms.IntegerField(required=False, widget=forms.HiddenInput)


class SettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        exclude = ["id"]
        labels = {
            "pickup_hours": "Abholung: Stunden vorher",
            "return_hours": "Rückgabe: Stunden vorher",
            "overdue_repeat_hours": "Überziehung: Wiederholung nach Stunden",
            "max_attempts": "Zustellversuche",
            "qualification_enabled": "Optionale Einweisungsnachricht aktivieren",
        }

    def clean(self):
        data = super().clean()
        if (
            not 1 <= data.get("overdue_repeat_hours", 0) <= 8760
            or not 1 <= data.get("max_attempts", 0) <= 10
        ):
            raise forms.ValidationError("Wiederholung 1–8760 Stunden; 1–10 Zustellversuche.")
        if any(data.get(k, 0) > 8760 for k in ("pickup_hours", "return_hours")):
            raise forms.ValidationError("Vorlauf höchstens 8760 Stunden.")
        return data
