import logging
from time import monotonic
from uuid import uuid4

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("deelvo.request")


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = str(uuid4())
        started = monotonic()
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        route = request.resolver_match.route if request.resolver_match else "unmatched"
        logger.info(
            "request",
            extra={
                "event": "http_request",
                "request_id": request_id,
                "status": response.status_code,
                "route": route,
                "duration_ms": round((monotonic() - started) * 1000, 2),
            },
        )
        return response


class AccountPrivacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == "/" or request.path.startswith(
            ("/konto/", "/inventar/", "/entdecken/", "/buchungen/", "/ausleihen/")
        ):
            response["Cache-Control"] = "no-store, private"
            response["Referrer-Policy"] = "same-origin"
            response["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            )
        return response
