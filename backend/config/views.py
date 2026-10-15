from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "foundation.html")


@require_safe
def live(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_safe
def ready(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
