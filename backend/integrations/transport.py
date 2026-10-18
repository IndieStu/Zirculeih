"""Strict transport parsing; domain services continue to validate business rules."""

import json
import re
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from django.core.exceptions import RequestDataTooBig


class APIError(Exception):
    def __init__(self, status, code, message="Anfrage konnte nicht verarbeitet werden."):
        self.status, self.code, self.message = status, code, message


def body(request, fields):
    if request.content_type != "application/json":
        raise APIError(415, "unsupported_media_type", "JSON erforderlich.")
    try:
        if int(request.META.get("CONTENT_LENGTH") or 0) > 65536:
            raise APIError(413, "payload_too_large")
        raw = request.body
    except RequestDataTooBig as exc:
        raise APIError(413, "payload_too_large") from exc
    if len(raw) > 65536:
        raise APIError(413, "payload_too_large")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def invalid(value):
        raise ValueError

    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise APIError(400, "invalid_json") from exc
    if not isinstance(data, dict) or set(data) - set(fields):
        raise APIError(400, "invalid_fields")
    return data


def text(data, key, *, maximum=500, required=True):
    value = data.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise APIError(400, "invalid_fields")
    return value


def uid(value):
    if not isinstance(value, str):
        raise APIError(400, "invalid_uuid")
    try:
        return UUID(value)
    except ValueError as exc:
        raise APIError(400, "invalid_uuid") from exc


def number(value, *, minimum=0, maximum=1000000000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise APIError(400, "invalid_fields")
    return value


def key(request, client):
    value = request.headers.get("Idempotency-Key", "")
    return uuid5(client.pk, str(uid(value)))


def etag(kind, row):
    return f'"{kind}-{row.pk}-{row.revision}"'


def revision(request, kind, row):
    value = request.headers.get("If-Match")
    if value is None:
        raise APIError(428, "precondition_required", "Aktuellen ETag als If-Match senden.")
    if value != etag(kind, row):
        raise APIError(409, "revision_conflict", "Objekt wurde inzwischen geändert.")
    return row.revision


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)", value
    ):
        raise APIError(400, "invalid_datetime", "RFC3339-Zeitpunkt mit Offset erforderlich.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not 1971 <= result.year <= 9998:
            raise ValueError
        return result
    except ValueError as exc:
        raise APIError(400, "invalid_datetime") from exc


def periods(policy, data):
    values: dict[str, Any] = {}
    for name in ["start", "end"]:
        raw = text(data, name, maximum=40)
        if policy.time_mode == "days":
            try:
                day = date.fromisoformat(raw)
                if day.isoformat() != raw:
                    raise ValueError
            except ValueError as exc:
                raise APIError(400, "invalid_date") from exc
            values[name] = day
        else:
            local = instant(raw).astimezone(ZoneInfo(policy.timezone))
            values[name] = local.replace(tzinfo=None)
            values[name + "_fold"] = local.fold
    for name in ["pickup_at", "return_at"]:
        if data.get(name) is not None:
            values[name] = instant(data[name]).astimezone(UTC)
    for name in ["unit_id", "pool_id"]:
        if data.get(name) is not None:
            values[name] = uid(data[name])
    for name in ["optional_ids"]:
        if name in data:
            value = data[name]
            if not isinstance(value, list) or len(value) > 20:
                raise APIError(400, "invalid_fields")
            values[name] = [uid(v) for v in value]
    return values


def filters(request, permitted):
    if set(request.GET) - set(permitted) or any(
        len(request.GET.getlist(k)) != 1 for k in request.GET
    ):
        raise APIError(400, "invalid_filter")
    if any(len(v) > 200 for v in request.GET.values()):
        raise APIError(400, "invalid_filter")


def paginate(request, rows):
    try:
        page = int(request.GET.get("page", "1"))
        size = int(request.GET.get("page_size", "30"))
    except ValueError as exc:
        raise APIError(400, "invalid_page") from exc
    if not 1 <= page <= 10000 or not 1 <= size <= 50:
        raise APIError(400, "invalid_page")
    total = len(rows)
    return {
        "count": total,
        "page": page,
        "page_size": size,
        "results": rows[(page - 1) * size : page * size],
    }


def iso(value):
    return value.isoformat() if value is not None else None
