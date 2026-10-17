from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError


def zone(name):
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValidationError("Bitte eine gültige IANA-Zeitzone wählen.") from exc


def local_instant(value, timezone_name, fold=None):
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValidationError("Bitte eine lokale Uhrzeit ohne impliziten Offset angeben.")
    tz = zone(timezone_name)
    choices = {}
    for candidate_fold in (0, 1):
        candidate = value.replace(tzinfo=tz, fold=candidate_fold)
        try:
            utc = candidate.astimezone(UTC)
            if utc.astimezone(tz).replace(tzinfo=None) == value:
                choices[candidate_fold] = utc
        except OverflowError as exc:
            raise ValidationError("Diese Uhrzeit liegt außerhalb des gültigen Bereichs.") from exc
    if not choices:
        raise ValidationError(
            "Diese lokale Uhrzeit existiert wegen der Zeitumstellung nicht.",
            code="nonexistent_time",
        )
    if len(set(choices.values())) > 1:
        if fold not in (0, 1):
            raise ValidationError(
                "Diese Uhrzeit kommt zweimal vor. Bitte die frühere oder spätere Uhrzeit wählen.",
                code="ambiguous_time",
            )
        return choices[fold]
    return next(iter(choices.values()))


def interval(policy, start, end, *, start_fold=None, end_fold=None):
    if policy.time_mode == "days":
        if type(start) is not date or type(end) is not date or end < start:
            raise ValidationError("Bitte gültige inklusive Kalendertage angeben.")
        try:
            exclusive = end + timedelta(days=1)
        except OverflowError as exc:
            raise ValidationError("Dieses Enddatum liegt außerhalb des gültigen Bereichs.") from exc
        s = local_instant(datetime.combine(start, datetime.min.time()), policy.timezone)
        e = local_instant(datetime.combine(exclusive, datetime.min.time()), policy.timezone)
        days = (exclusive - start).days
        return s, e, days * 1440, start, exclusive
    s = local_instant(start, policy.timezone, start_fold)
    e = local_instant(end, policy.timezone, end_fold)
    return s, e, (e - s).total_seconds() / 60, None, None


def aware_interval(start, end):
    if (
        not isinstance(start, datetime)
        or not isinstance(end, datetime)
        or start.tzinfo is None
        or end.tzinfo is None
        or end <= start
    ):
        raise ValidationError("Ein positiver Zeitraum mit Zeitzone ist erforderlich.")
