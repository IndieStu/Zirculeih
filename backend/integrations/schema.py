"""Explicit OpenAPI contract from the same fixed route registry as the adapter."""

import re
from typing import Any

from django.http import JsonResponse

from .api import ROUTES

UUID = {"type": "string", "format": "uuid"}
TEXT = {"type": "string"}
BOOL = {"type": "boolean"}
REV = {"type": "integer", "minimum": 1}
STAMP = {"type": "string", "format": "date-time"}
NULLSTAMP = {"type": ["string", "null"], "format": "date-time"}


def obj(properties, required=()):
    return dict(
        type="object", properties=properties, required=list(required), additionalProperties=False
    )


def array(item, maximum=50):
    return dict(type="array", items=item, maxItems=maximum)


def ref(name):
    return {"$ref": "#/components/schemas/" + name}


PERIOD: dict[str, Any] = {
    k: {
        "type": "string",
        "maxLength": 40,
        "description": "ISO date in day mode (end inclusive), otherwise RFC3339 offset instant.",
    }
    for k in ["start", "end"]
}
PERIOD.update(
    pickup_at=STAMP,
    return_at=STAMP,
    unit_id=UUID,
    pool_id=UUID,
    optional_ids=array(UUID, 20),
    resource_id=UUID,
)

SCHEMAS = {
    "Error": obj(
        {
            "error": obj(
                {"code": TEXT, "message": TEXT, "request_id": UUID},
                ["code", "message", "request_id"],
            )
        },
        ["error"],
    ),
    "Asset": obj(
        {
            "id": UUID,
            "inventory_number": TEXT,
            "name": TEXT,
            "condition": TEXT,
            "lifecycle": TEXT,
            "location_id": UUID,
            "category_id": UUID,
            "revision": REV,
        },
        [
            "id",
            "inventory_number",
            "name",
            "condition",
            "lifecycle",
            "location_id",
            "category_id",
            "revision",
        ],
    ),
    "Resource": obj(
        {
            "id": UUID,
            "title": TEXT,
            "slug": TEXT,
            "summary": TEXT,
            "location_label": TEXT,
            "resource_type": TEXT,
            "time_mode": {"enum": ["slots", "days"]},
            "timezone": TEXT,
            "revision": {"type": "integer", "minimum": 0},
        },
        [
            "id",
            "title",
            "slug",
            "summary",
            "location_label",
            "resource_type",
            "time_mode",
            "timezone",
            "revision",
        ],
    ),
    "Booking": obj(
        {
            "id": UUID,
            "resource_id": UUID,
            "unit_id": UUID,
            "status": TEXT,
            "start": STAMP,
            "end": STAMP,
            "start_date": {"type": ["string", "null"], "format": "date"},
            "end_date_exclusive": {"type": ["string", "null"], "format": "date"},
            "timezone": TEXT,
            "revision": REV,
        },
        [
            "id",
            "resource_id",
            "unit_id",
            "status",
            "start",
            "end",
            "start_date",
            "end_date_exclusive",
            "timezone",
            "revision",
        ],
    ),
    "LoanLine": obj(
        {
            "id": UUID,
            "booking_id": UUID,
            "resource_id": UUID,
            "asset_id": UUID,
            "expected_return": STAMP,
            "returned_at": NULLSTAMP,
            "revision": REV,
        },
        [
            "id",
            "booking_id",
            "resource_id",
            "asset_id",
            "expected_return",
            "returned_at",
            "revision",
        ],
    ),
    "Loan": obj(
        {"id": UUID, "issued_at": STAMP, "closed_at": NULLSTAMP, "lines": array(ref("LoanLine"))},
        ["id", "issued_at", "closed_at", "lines"],
    ),
    "Import": obj(
        {
            "id": UUID,
            "expires_at": STAMP,
            "committed_at": NULLSTAMP,
            "row_count": {"type": "integer", "minimum": 1, "maximum": 200},
            "created_asset_ids": array(UUID, 200),
        },
        ["id", "expires_at", "committed_at", "row_count", "created_asset_ids"],
    ),
    "Period": obj(PERIOD, ["resource_id", "start", "end"]),
    "Availability": obj(
        {
            "code": TEXT,
            "unit_id": {"type": ["string", "null"], "format": "uuid"},
            "policy_revision": {"type": ["integer", "null"]},
        },
        ["code", "unit_id", "policy_revision"],
    ),
    "Move": obj(
        {"location_id": UUID, "reason": {"type": "string", "minLength": 1, "maxLength": 500}},
        ["location_id", "reason"],
    ),
    "Reason": obj({"reason": {"type": "string", "minLength": 1, "maxLength": 500}}, ["reason"]),
    "Resolve": obj(
        {"namespace_id": UUID, "code": {"type": "string", "minLength": 1, "maxLength": 256}},
        ["namespace_id", "code"],
    ),
    "Resolution": obj(
        {
            "status": TEXT,
            "asset_id": {"type": ["string", "null"], "format": "uuid"},
            "unit_id": {"type": ["string", "null"], "format": "uuid"},
            "resource_id": {"type": ["string", "null"], "format": "uuid"},
        },
        ["status", "asset_id", "unit_id", "resource_id"],
    ),
    "CSVImport": obj({"csv": {"type": "string", "minLength": 1, "maxLength": 60000}}, ["csv"]),
    "Empty": obj({}),
    "Checkout": obj(
        {
            "borrower_id": UUID,
            "bookings": array(
                obj(
                    {
                        "booking_id": UUID,
                        "condition": {"enum": ["good", "worn", "damaged", "inspection"]},
                        "accessories_checked": BOOL,
                        "accessories": {"type": "string", "maxLength": 2000},
                    },
                    ["booking_id", "condition", "accessories_checked"],
                )
            ),
        },
        ["borrower_id", "bookings"],
    ),
    "Return": obj(
        {
            "lines": array(
                obj(
                    {
                        "line_id": UUID,
                        "revision": REV,
                        "condition": {"enum": ["good", "worn", "damaged", "inspection"]},
                        "accessories_checked": BOOL,
                        "note": {"type": "string", "maxLength": 2000},
                    },
                    ["line_id", "revision", "condition", "accessories_checked"],
                )
            )
        },
        ["lines"],
    ),
}
BODY = {
    "move": "Move",
    "resolve": "Resolve",
    "import_create": "CSVImport",
    "import_commit": "Empty",
    "confirm": "Period",
    "availability": "Period",
    "cancel": "Reason",
    "checkout": "Checkout",
    "return": "Return",
}
OUTPUT = {
    "resources": "Resource",
    "assets": "Asset",
    "asset": "Asset",
    "move": "Asset",
    "resolve": "Resolution",
    "import_create": "Import",
    "import_read": "Import",
    "import_commit": "Import",
    "availability": "Availability",
    "bookings": "Booking",
    "confirm": "Booking",
    "booking": "Booking",
    "cancel": "Booking",
    "loans": "Loan",
    "loan": "Loan",
    "checkout": "Loan",
    "return": "Loan",
}
FILTERS = {
    "resources": ["q"],
    "assets": ["q", "location_id", "category_id", "condition", "lifecycle"],
    "export": ["q", "location_id", "category_id", "condition", "lifecycle"],
    "bookings": ["view", "resource_id"],
    "loans": ["view"],
}
PAGED = {"resources", "assets", "bookings", "loans"}


def contract():
    paths: dict[str, Any] = {}
    for method, pattern, cap, write, name in ROUTES:
        path = "/" + re.sub(r"\(\?P<id>.*?\)", "{id}", pattern)
        params = []
        if "{id}" in path:
            params.append(dict(name="id", in_="path", required=True, schema=UUID))
        for field in FILTERS.get(name, []):
            params.append(dict(name=field, in_="query", required=False, schema=TEXT))
        if name in PAGED:
            for field, maximum, default in [("page", 10000, 1), ("page_size", 50, 30)]:
                params.append(
                    dict(
                        name=field,
                        in_="query",
                        required=False,
                        schema={
                            "type": "integer",
                            "minimum": 1,
                            "maximum": maximum,
                            "default": default,
                        },
                    )
                )
        if name in {"confirm", "checkout", "return"}:
            params.append(
                dict(
                    name="Idempotency-Key",
                    in_="header",
                    required=True,
                    schema=UUID,
                    description=(
                        "Client-namespaced UUID; reuse identical payload after "
                        "a network interruption."
                    ),
                )
            )
        if name in {"move", "cancel"}:
            params.append(
                dict(
                    name="If-Match",
                    in_="header",
                    required=True,
                    schema=TEXT,
                    description="Exact strong ETag from the current object GET.",
                )
            )
        params = [{("in" if k == "in_" else k): v for k, v in p.items()} for p in params]
        result = ref(OUTPUT[name]) if name in OUTPUT else TEXT
        if name in PAGED:
            result = obj(
                {
                    "count": {"type": "integer", "minimum": 0},
                    "page": {"type": "integer"},
                    "page_size": {"type": "integer"},
                    "results": array(result),
                },
                ["count", "page", "page_size", "results"],
            )
        status = "201" if name in {"confirm", "checkout", "import_create"} else "200"
        mime = "text/csv" if name == "export" else "application/json"
        responses = {
            status: {
                "description": "Current authorized projection",
                "content": {mime: {"schema": result}},
            }
        }
        for code in [
            "400",
            "401",
            "403",
            "404",
            "405",
            "409",
            "413",
            "415",
            "422",
            "428",
            "429",
            "500",
        ]:
            responses[code] = {
                "description": "Bounded machine error; see error.code.",
                "content": {"application/json": {"schema": ref("Error")}},
            }
        operation = dict(
            operationId=name,
            summary=name.replace("_", " "),
            security=[{"bearerAuth": []}],
            parameters=params,
            responses=responses,
            **{"x-deelvo-capability": cap, "x-deelvo-domain-write": write},
        )
        if name in BODY:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": ref(BODY[name])}},
            }
        paths.setdefault(path, {})[method.lower()] = operation
    return dict(
        openapi="3.1.1",
        info={
            "title": "Deelvo integration API",
            "version": "1.0.0",
            "description": (
                "Explicit self-hosted adapters. Current owner rights intersect "
                "client/token ceilings. No authorization server or master key."
            ),
        },
        servers=[{"url": "/api/v1"}],
        paths=paths,
        components={
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "Deelvo opaque dv1 token",
                }
            },
            "schemas": SCHEMAS,
        },
    )


def view(request):
    if request.method not in {"GET", "HEAD"}:
        from .api import error

        return error(request, 405, "method_not_allowed", "GET verwenden.")
    response = JsonResponse(contract(), json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'inline; filename="deelvo-openapi-v1.json"'
    response["X-Content-Type-Options"] = "nosniff"
    return response
