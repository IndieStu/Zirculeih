from uuid import uuid4

from accounts.authorization import allowed
from django import forms
from inventory.models import Asset, IdentifierNamespace
from inventory.services import asset_scope, visible_assets
from resources.models import Resource
from resources.services import resource_scope

from .models import Agreement


class AgreementForm(forms.Form):
    title = forms.CharField(label="Titel", max_length=200)
    kind = forms.ChoiceField(label="Art", choices=Agreement._meta.get_field("kind").choices)
    text = forms.CharField(label="Text der Organisation", max_length=50000, widget=forms.Textarea)


class VersionForm(forms.Form):
    text = forms.CharField(
        label="Neuer vollständiger Text", max_length=50000, widget=forms.Textarea
    )


class AssignmentForm(forms.Form):
    agreement = forms.ModelChoiceField(
        label="Zusatzvereinbarung", queryset=Agreement.objects.none()
    )
    resource = forms.ModelChoiceField(
        label="Angebot (alternativ zum Asset)", queryset=Resource.objects.none(), required=False
    )
    asset = forms.ModelChoiceField(
        label="Asset (alternativ zum Angebot)", queryset=Asset.objects.none(), required=False
    )

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agreement"].queryset = Agreement.objects.filter(
            kind="additional", is_active=True
        )
        self.fields["resource"].queryset = Resource.objects.filter(
            pk__in=[
                r.pk
                for r in Resource.objects.all()
                if allowed(actor, "agreement.assign", resource_scope(r))
            ]
        )
        self.fields["asset"].queryset = visible_assets(actor).filter(
            pk__in=[
                a.pk
                for a in visible_assets(actor)
                if allowed(actor, "agreement.assign", asset_scope(a))
            ]
        )


class ScanForm(forms.Form):
    namespace = forms.ModelChoiceField(
        label="Namensraum", queryset=IdentifierNamespace.objects.filter(is_active=True)
    )
    code = forms.CharField(
        label="Code scannen oder eingeben",
        max_length=200,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "off"}),
    )


class ReturnForm(forms.Form):
    condition = forms.ChoiceField(
        label="Rückgabezustand",
        choices=[
            ("good", "Gut"),
            ("worn", "Gebraucht"),
            ("damaged", "Beschädigt"),
            ("inspection", "Prüfung erforderlich"),
        ],
    )
    accessories_checked = forms.BooleanField(
        label="Zubehör vollständig geprüft; Abweichungen in der Notiz dokumentiert"
    )
    note = forms.CharField(
        label="Notiz ohne unnötige Personendaten",
        max_length=2000,
        widget=forms.Textarea,
        required=False,
    )
    key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)


class ExtensionForm(forms.Form):
    end = forms.CharField(label="Neues Ende", max_length=30)
    return_at = forms.CharField(
        label="Neuer Rückgabetermin lokal",
        max_length=30,
        widget=forms.TextInput(attrs={"type": "datetime-local"}),
    )
    return_fold = forms.ChoiceField(
        label="Rückgabetermin bei Herbstumstellung",
        choices=[("", "Eindeutig"), ("0", "Erste Instanz"), ("1", "Zweite Instanz")],
        required=False,
    )
    end_fold = forms.ChoiceField(
        label="Ende bei Herbstumstellung",
        choices=[("", "Eindeutig"), ("0", "Erste Instanz"), ("1", "Zweite Instanz")],
        required=False,
    )
    reason = forms.CharField(label="Grund", max_length=500)
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=1)

    def __init__(self, policy, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = policy
        self.fields["end"].widget = forms.TextInput(
            attrs={"type": "date" if policy.time_mode == "days" else "datetime-local"}
        )

    def clean(self):
        from datetime import date, datetime

        from bookings.time_rules import local_instant

        data = super().clean()
        try:
            if data.get("end"):
                data["end"] = (
                    date.fromisoformat
                    if self.policy.time_mode == "days"
                    else datetime.fromisoformat
                )(data["end"])
            if data.get("return_at"):
                data["return_at"] = local_instant(
                    datetime.fromisoformat(data["return_at"]),
                    self.policy.timezone,
                    int(data["return_fold"]) if data.get("return_fold") else None,
                )
        except (ValueError, forms.ValidationError) as exc:
            self.add_error(
                None, exc if isinstance(exc, forms.ValidationError) else "Ungültiges Datum."
            )
        data["end_fold"] = int(data["end_fold"]) if data.get("end_fold") else None
        return data
