from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .authorization import ACTION_LABELS, ACTIONS, SYSTEM_ACTIONS
from .models import Group, User


class SignupForm(forms.Form):
    email = forms.EmailField(label="E-Mail", max_length=254)
    password = forms.CharField(label="Passwort", widget=forms.PasswordInput, min_length=12)
    password_confirm = forms.CharField(label="Passwort wiederholen", widget=forms.PasswordInput)
    privacy = forms.BooleanField(label="Ich habe die Datenschutzhinweise gelesen.")

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("password_confirm"):
            raise forms.ValidationError("Die Passwörter stimmen nicht überein.")
        return data


class EmailForm(forms.Form):
    email = forms.EmailField(label="E-Mail", max_length=254)


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="E-Mail", max_length=254)


class ResetForm(forms.Form):
    password = forms.CharField(label="Neues Passwort", widget=forms.PasswordInput, min_length=12)
    password_confirm = forms.CharField(label="Passwort wiederholen", widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("password_confirm"):
            raise forms.ValidationError("Die Passwörter stimmen nicht überein.")
        return data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "street", "postal_code", "city", "country", "phone"]
        labels = {
            "full_name": "Vollständiger Name",
            "street": "Straße und Hausnummer",
            "postal_code": "Postleitzahl",
            "city": "Ort",
            "country": "Land",
            "phone": "Telefonnummer",
        }


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "description", "is_active"]
        labels = {"name": "Name", "description": "Beschreibung", "is_active": "Aktiv"}


class GrantForm(forms.Form):
    action = forms.ChoiceField(
        label="Aktion",
        choices=[("", "Bitte wählen")]
        + [(a, ACTION_LABELS[a]) for a in sorted(ACTIONS - SYSTEM_ACTIONS)],
    )
    effect = forms.ChoiceField(
        label="Wirkung", choices=[("allow", "Erlauben"), ("deny", "Verweigern")]
    )
    scope_kind = forms.ChoiceField(
        label="Geltungsbereich",
        choices=[
            ("organization", "Gesamte Organisation"),
            ("group", "Eine Gruppe (Mitgliedschaften)"),
            ("user", "Ein Konto (Kontosperre)"),
        ],
    )
    scope_group = forms.ModelChoiceField(
        label="Zielgruppe",
        required=False,
        queryset=Group.objects.filter(is_active=True, archived_at__isnull=True).order_by("name"),
    )
    scope_email = forms.EmailField(label="E-Mail des Zielkontos", required=False)
    max_horizon_days = forms.IntegerField(label="Max. Tage im Voraus", min_value=0, required=False)
    max_duration_minutes = forms.IntegerField(
        label="Max. Dauer in Minuten", min_value=1, required=False
    )

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        from inventory.forms import NodeChoice, permitted_nodes
        from inventory.models import Asset, Category, Location
        from inventory.services import visible_assets
        from resources.models import Resource
        from resources.services import visible_resources

        self.fields["scope_kind"].choices += [
            ("location", "Ein Standort"),
            ("category", "Eine Kategorie"),
            ("asset", "Ein Asset"),
            ("resource", "Ein Angebot"),
        ]
        self.fields["scope_location"] = NodeChoice(
            label="Zielstandort",
            required=False,
            queryset=permitted_nodes(actor, Location, "location.read")
            if actor
            else Location.objects.none(),
        )
        self.fields["scope_category"] = NodeChoice(
            label="Zielkategorie",
            required=False,
            queryset=permitted_nodes(actor, Category, "category.read")
            if actor
            else Category.objects.none(),
        )
        self.fields["scope_asset"] = forms.ModelChoiceField(
            label="Zielasset",
            required=False,
            queryset=visible_assets(actor) if actor else Asset.objects.none(),
        )
        self.fields["inherit"] = forms.BooleanField(
            label="Auch untergeordnete Standorte/Kategorien", required=False
        )
        self.fields["scope_resource"] = forms.ModelChoiceField(
            label="Zielangebot",
            required=False,
            queryset=visible_resources(actor, management=True)
            if actor
            else Resource.objects.none(),
        )

    def clean(self):
        data = super().clean()
        group, email = data.pop("scope_group", None), data.pop("scope_email", "")
        kind = data.get("scope_kind")
        targets = {
            k: data.pop("scope_" + k, None) for k in ("location", "category", "asset", "resource")
        }
        if kind in targets:
            target = targets[kind]
            if target is None or group or email or any(v for k, v in targets.items() if k != kind):
                raise forms.ValidationError("Bitte genau ein passendes Zielobjekt auswählen.")
            data["scope_id"] = target.pk
            return data
        if any(targets.values()):
            raise forms.ValidationError("Bitte keine weiteren Zielobjekte angeben.")
        if kind == "group":
            if not group or email:
                raise forms.ValidationError("Bitte genau eine Zielgruppe wählen.")
            data["scope_id"] = group.pk
        elif kind == "user":
            user = User.objects.filter(email__iexact=email).first()
            if not user or group:
                raise forms.ValidationError("Bitte genau ein bestehendes Zielkonto angeben.")
            data["scope_id"] = user.pk
        else:
            if group or email:
                raise forms.ValidationError(
                    "Für die Organisation keine Zielgruppe oder Konto angeben."
                )
            data["scope_id"] = None
        return data


class MembershipForm(forms.Form):
    email = forms.EmailField(label="Konto-E-Mail")
    remove = forms.BooleanField(label="Mitgliedschaft entfernen", required=False)


class SuspensionForm(forms.Form):
    suspended = forms.BooleanField(label="Konto sperren", required=False)
    reason = forms.CharField(label="Grund (keine sensiblen Daten)", max_length=500)


class ReauthenticateForm(forms.Form):
    password = forms.CharField(label="Lokales Passwort zur Bestätigung", widget=forms.PasswordInput)
