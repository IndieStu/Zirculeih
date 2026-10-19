import json
import logging
from unittest.mock import patch
from uuid import UUID

import pytest
from config.logging import JsonFormatter
from django.db import OperationalError
from django.test import Client, override_settings


def test_live_without_database(client):
    with patch("config.views.connection.cursor", side_effect=AssertionError("No DB for live")):
        response = client.get("/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response["X-Request-ID"])


@pytest.mark.django_db
@pytest.mark.postgres
def test_ready_with_postgresql(client):
    assert client.get("/health/ready/").status_code == 200


def test_ready_failure_does_not_leak_database_details(client):
    with patch("config.views.connection.cursor", side_effect=OperationalError("secret-host")):
        response = client.get("/health/ready/")
    assert response.status_code == 503
    assert b"secret-host" not in response.content


@override_settings(SECURE_SSL_REDIRECT=False)
@pytest.mark.django_db
def test_foundation_and_request_id(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b'lang="de-de"' in response.content
    assert UUID(response["X-Request-ID"])


@override_settings(SECURE_SSL_REDIRECT=True)
def test_secure_redirect_exempts_only_health(client):
    assert client.get("/").status_code == 301
    assert client.get("/health/live/").status_code == 200


def test_health_is_read_only(client):
    assert client.post("/health/live/").status_code == 405


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=["localhost"])
def test_unknown_host_rejected():
    assert Client().get("/", HTTP_HOST="attacker.invalid").status_code == 400


def test_logs_omit_sensitive_message_and_query():
    record = logging.LogRecord("django", logging.ERROR, "", 0, "secret?token=abc", (), None)
    data = json.loads(JsonFormatter().format(record))
    assert data["event"] == "application_log"
    assert "secret" not in json.dumps(data)
