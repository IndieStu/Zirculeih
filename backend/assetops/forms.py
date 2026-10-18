from accounts.authorization import allowed
from django import forms
from inventory.forms import permitted_nodes
from inventory.models import Asset, Category, IdentifierNamespace, Location
from inventory.services import visible_assets

from .models import InventoryRun, MaintenanceTask


class RunForm(forms.Form):
    title = forms.CharField(label="Name des Inventurlaufs", max_length=150)
    scope = forms.ChoiceField(
        label="Erwarteter Bereich", choices=InventoryRun._meta.get_field("scope").choices
    )
    location = forms.ModelChoiceField(
        label="Standort", queryset=Location.objects.none(), required=False
    )
    category = forms.ModelChoiceField(
        label="Kategorie", queryset=Category.objects.none(), required=False
    )

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, model in [("location", Location), ("category", Category)]:
            self.fields[key].queryset = permitted_nodes(actor, model, "inventory_run.create")

        choices = []
        for key, label in InventoryRun._meta.get_field("scope").choices:
            if (key == "organization" and allowed(actor, "inventory_run.create")) or (
                key in {"location", "category"} and self.fields[key].queryset.exists()
            ):
                choices.append((key, label))
        self.fields["scope"].choices = choices

    def clean(self):
        data = super().clean()
        scope = data.get("scope")
        if scope in {"location", "category"} and not data.get(scope):
            raise forms.ValidationError("Den Bereich bitte konkret auswählen.")
        data["scope_id"] = (
            data[scope].pk if scope in {"location", "category"} and data.get(scope) else None
        )
        return data


class ScanForm(forms.Form):
    namespace = forms.ModelChoiceField(
        label="Code-Namensraum", queryset=IdentifierNamespace.objects.filter(is_active=True)
    )
    code = forms.CharField(
        label="Code scannen oder eingeben",
        max_length=256,
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "data-scan-input": "", "autofocus": True}
        ),
    )
    location = forms.ModelChoiceField(
        label="Tatsächlicher Beobachtungsort", queryset=Location.objects.none()
    )
    request_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = permitted_nodes(actor, Location, "location.read")


class TaskForm(forms.ModelForm):
    assign_self = forms.BooleanField(label="Ich übernehme den Auftrag", required=False)

    class Meta:
        model = MaintenanceTask
        fields = ["asset", "title", "kind", "description", "due_date", "interval_days"]
        labels = {
            "asset": "Asset",
            "title": "Auftrag",
            "kind": "Art",
            "description": "Beschreibung",
            "due_date": "Fällig am",
            "interval_days": "Folgeprüfung nach Tagen (optional)",
        }
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = visible_assets(actor, "maintenance.manage").values_list("pk", flat=True)
        self.fields["asset"].queryset = visible_assets(actor).filter(
            pk__in=allowed, archived_at__isnull=True
        )


class BulkForm(forms.Form):
    assets = forms.ModelMultipleChoiceField(
        label="Assets wählen (höchstens 100)", queryset=Asset.objects.none()
    )
    action = forms.ChoiceField(
        label="Aktion", choices=[("move", "Standort ändern"), ("condition", "Zustand ändern")]
    )
    location = forms.ModelChoiceField(
        label="Neuer Standort", queryset=Location.objects.none(), required=False
    )
    condition = forms.ChoiceField(
        label="Neuer Zustand",
        choices=[("", "Bitte wählen"), *Asset.Condition.choices],
        required=False,
    )
    reason = forms.CharField(label="Begründung", max_length=500)

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assets"].queryset = visible_assets(actor).filter(archived_at__isnull=True)
        self.fields["location"].queryset = permitted_nodes(actor, Location, "location.read")

    def clean(self):
        data = super().clean()
        if data.get("action") == "move" and not data.get("location"):
            raise forms.ValidationError("Zielstandort wählen.")
        if data.get("action") == "condition" and not data.get("condition"):
            raise forms.ValidationError("Zustand wählen.")
        if len(data.get("assets", [])) not in range(1, 101):
            raise forms.ValidationError("1–100 Assets wählen.")
        return data
