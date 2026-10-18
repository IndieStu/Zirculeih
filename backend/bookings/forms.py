from datetime import date, datetime
from uuid import uuid4

from accounts.authorization import allowed
from django import forms
from inventory.forms import NodeChoice, permitted_nodes
from inventory.models import Category, Location
from resources.models import Resource
from resources.services import resource_scope

from .models import BookingPolicy, ResourceBlock, ScheduleException, ScheduleWindow
from .time_rules import local_instant

FOLDS = [
    ("", "Bitte wählen"),
    ("0", "Frühere Uhrzeit"),
    ("1", "Spätere Uhrzeit"),
]


class BookingForm(forms.Form):
    start = forms.CharField(label="Von", max_length=30)
    end = forms.CharField(label="Bis", max_length=30)
    start_fold = forms.ChoiceField(
        label="Beginn bei doppelter Herbst-Uhrzeit", choices=FOLDS, required=False
    )
    end_fold = forms.ChoiceField(
        label="Ende bei doppelter Herbst-Uhrzeit", choices=FOLDS, required=False
    )
    key = forms.UUIDField(widget=forms.HiddenInput, initial=uuid4)

    def __init__(self, policy, *args, needs_appointments=False, choose_capacity=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.policy = policy
        from resources.models import ResourcePool

        from .services import candidates

        units = candidates(policy.resource).exclude(public_name="")
        pools = ResourcePool.objects.filter(resource=policy.resource, is_active=True).exclude(
            public_name=""
        )
        self.fields["unit_id"] = forms.ChoiceField(
            label="Exemplar / Platz",
            required=False,
            choices=[("", "Automatisch zuweisen"), *[(str(u.pk), u.public_name) for u in units]],
        )
        self.fields["pool_id"] = forms.ChoiceField(
            label="Pool",
            required=False,
            choices=[
                ("", "Alle geeigneten Exemplare"),
                *[(str(p.pk), p.public_name) for p in pools],
            ],
        )
        for name in ("unit_id", "pool_id"):
            if not choose_capacity or len(self.fields[name].choices) == 1:
                self.fields.pop(name)
        kind = "date" if policy.time_mode == "days" else "datetime-local"
        for field in ("start", "end"):
            self.fields[field].widget = forms.TextInput(attrs={"type": kind})
        if policy.use_mode == "physical_loan" or needs_appointments:
            for field, label in (
                ("pickup_at", "Abholung"),
                ("return_at", "Rückgabe"),
            ):
                self.fields[field] = forms.CharField(
                    label=label,
                    max_length=30,
                    widget=forms.TextInput(attrs={"type": "datetime-local"}),
                )
                self.fields[field + "_fold"] = forms.ChoiceField(
                    label=label + " bei Herbstumstellung", choices=FOLDS, required=False
                )
        if kind == "date":
            self.fields["end"].label = "Bis einschließlich"
            self.fields.pop("start_fold")
            self.fields.pop("end_fold")

        # Ask only when the submitted local time really has two valid instants.
        for name in list(self.fields):
            if not name.endswith("_fold"):
                continue
            base = name.removesuffix("_fold")
            self.fields[name].widget = forms.HiddenInput()
            if self.is_bound:
                try:
                    raw = self.data.get(self.add_prefix(base), "")
                    local_instant(datetime.fromisoformat(raw), policy.timezone)
                except forms.ValidationError as exc:
                    if exc.code == "ambiguous_time":
                        self.fields[name].widget = forms.Select(choices=FOLDS)
                        self.fields[name].label = self.fields[base].label + ": welche Uhrzeit?"
                        self.fields[name].help_text = (
                            "Diese Uhrzeit kommt an diesem Tag zweimal vor. "
                            "Meinst du die frühere oder die spätere Uhrzeit?"
                        )
                except ValueError:
                    pass

    def clean(self):
        data = super().clean()
        parser = date.fromisoformat if self.policy.time_mode == "days" else datetime.fromisoformat
        for field in ("start", "end"):
            if field in data:
                try:
                    data[field] = parser(data[field])
                except ValueError:
                    self.add_error(
                        field, "Bitte ein gültiges Datum bzw. eine lokale Uhrzeit eingeben."
                    )
        for field in ("start_fold", "end_fold"):
            data[field] = int(data[field]) if data.get(field) else None
        if self.policy.time_mode != "days":
            for field in ("start", "end"):
                if field in data:
                    try:
                        local_instant(data[field], self.policy.timezone, data[field + "_fold"])
                    except forms.ValidationError as exc:
                        self.add_error(field, exc)
        if "pickup_at" in self.fields:
            for field in ("pickup_at", "return_at"):
                if data.get(field):
                    try:
                        fold = int(data[field + "_fold"]) if data.get(field + "_fold") else None
                        data[field] = local_instant(
                            datetime.fromisoformat(data[field]), self.policy.timezone, fold
                        )
                    except (ValueError, forms.ValidationError) as exc:
                        self.add_error(
                            field,
                            exc if isinstance(exc, forms.ValidationError) else "Ungültige Uhrzeit.",
                        )
        return data


class PolicyForm(forms.ModelForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)

    class Meta:
        model = BookingPolicy
        exclude = ["resource", "revision", "requires_qualification", "requires_agreement"]
        labels = {
            "use_mode": "Nutzungsart",
            "approval_mode": "Bestätigung",
            "max_occurrences": "Höchstens Termine je Serie",
            "time_mode": "Zeitmodus",
            "timezone": "Zeitzone",
            "granularity_minutes": "Zeitraster (Minuten)",
            "min_duration_minutes": "Mindestdauer (Minuten)",
            "max_duration_minutes": "Höchstdauer (Minuten)",
            "min_days": "Mindesttage",
            "max_days": "Höchsttage",
            "max_horizon_days": "Maximaler Vorlauf (Kalendertage)",
            "lead_minutes": "Mindestvorlauf (Minuten)",
            "buffer_before_minutes": "Vorbereitung vorher (Minuten)",
            "buffer_after_minutes": "Übergangszeit danach (Minuten)",
            "max_parallel": "Maximal gleichzeitige Buchungen je Konto",
            "cancellation_notice_minutes": "Stornofrist vor Beginn (Minuten)",
            "requires_qualification": "Einweisung erforderlich",
            "requires_agreement": "Zusatzvereinbarung erforderlich",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expected_revision"].initial = self.instance.revision


def owner_choices(form, actor, action):
    form.fields["resource"].queryset = Resource.objects.filter(
        pk__in=[r.pk for r in Resource.objects.all() if allowed(actor, action, resource_scope(r))]
    )
    form.fields["location"] = NodeChoice(
        label="Standort",
        required=False,
        queryset=permitted_nodes(actor, Location, action),
    )
    form.fields["resource"].label = "Artikel / Raum"
    if "category" in form.fields:
        form.fields["category"] = NodeChoice(
            label="Kategorie",
            required=False,
            queryset=permitted_nodes(actor, Category, action),
        )
        form.fields["organization"].label = "Gesamte Organisation"
        if not allowed(actor, action):
            form.fields["organization"].disabled = True


class WindowForm(forms.ModelForm):
    weekday = forms.TypedChoiceField(
        label="Wochentag",
        coerce=int,
        choices=list(
            enumerate(
                ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            )
        ),
    )

    class Meta:
        model = ScheduleWindow
        fields = [
            "resource",
            "location",
            "category",
            "organization",
            "purpose",
            "weekday",
            "start_time",
            "end_time",
            "end_next_day",
        ]
        labels = {
            "purpose": "Zeitplanart",
            "weekday": "Wochentag",
            "start_time": "Von",
            "end_time": "Bis",
            "end_next_day": "Ende am Folgetag",
        }
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_choices(self, actor, "booking.configure")


class ExceptionForm(forms.ModelForm):
    through = forms.DateField(
        label="Bis einschließlich (optional)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self):
        data = super().clean()
        if data.get("through") and data.get("date"):
            days = (data["through"] - data["date"]).days
            if not 0 <= days <= 366:
                self.add_error("through", "Bitte einen Zeitraum von höchstens einem Jahr wählen.")
        return data

    class Meta:
        model = ScheduleException
        fields = [
            "resource",
            "location",
            "category",
            "organization",
            "purpose",
            "date",
            "is_closed",
            "start_time",
            "end_time",
            "end_next_day",
        ]
        labels = {
            "purpose": "Zeitplanart",
            "date": "Ausnahmedatum",
            "is_closed": "An diesem Datum geschlossen",
            "start_time": "Abweichend von",
            "end_time": "Abweichend bis",
            "end_next_day": "Ende am Folgetag",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_choices(self, actor, "booking.configure")


class BlockForm(forms.ModelForm):
    local_start = forms.CharField(
        label="Beginn lokal",
        widget=forms.TextInput(attrs={"type": "datetime-local"}),
        max_length=30,
    )
    local_end = forms.CharField(
        label="Ende lokal", widget=forms.TextInput(attrs={"type": "datetime-local"}), max_length=30
    )
    timezone_name = forms.CharField(label="IANA-Zeitzone", initial="Europe/Berlin", max_length=64)
    start_fold = forms.ChoiceField(
        label="Beginn bei Herbstumstellung", choices=FOLDS, required=False
    )
    end_fold = forms.ChoiceField(label="Ende bei Herbstumstellung", choices=FOLDS, required=False)

    class Meta:
        model = ResourceBlock
        fields = ["resource", "location", "reason"]
        labels = {"reason": "Interner Grund (keine unnötigen Personendaten)"}

    def __init__(self, actor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_choices(self, actor, "booking.block")

    def clean(self):
        data = super().clean()
        for field in ("start", "end"):
            if data.get("local_" + field) and data.get("timezone_name"):
                try:
                    fold = int(data[field + "_fold"]) if data.get(field + "_fold") else None
                    data[field] = local_instant(
                        datetime.fromisoformat(data["local_" + field]), data["timezone_name"], fold
                    )
                except (ValueError, forms.ValidationError) as exc:
                    self.add_error(
                        "local_" + field,
                        exc if isinstance(exc, forms.ValidationError) else "Ungültige Uhrzeit.",
                    )
        return data


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Grund", max_length=500)
    revision = forms.IntegerField(widget=forms.HiddenInput, required=False, min_value=0)


class RecurrenceForm(forms.Form):
    weekdays = forms.MultipleChoiceField(
        label="Wöchentlich an",
        required=False,
        choices=list(
            enumerate(
                ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
            )
        ),
        widget=forms.CheckboxSelectMultiple,
    )
    count = forms.IntegerField(label="Anzahl Termine", min_value=1, max_value=366, required=False)
    until = forms.DateField(
        label="Oder letzter Serientag",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self):
        data = super().clean()
        if data.get("weekdays") and bool(data.get("count")) == bool(data.get("until")):
            raise forms.ValidationError("Für Serien entweder Anzahl oder Enddatum wählen.")
        if not data.get("weekdays") and (data.get("count") or data.get("until")):
            raise forms.ValidationError("Für Serien Wochentage auswählen.")
        data["weekdays"] = [int(v) for v in data.get("weekdays", [])]
        return data
