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

    def clean(self):
        data = super().clean()
        group, email = data.pop("scope_group", None), data.pop("scope_email", "")
        kind = data.get("scope_kind")
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
