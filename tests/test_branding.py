"""Verify delivered branding assets and the accessible color combinations actually used."""

import hashlib
import json
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.test import override_settings


def contrast(a, b):
    def luminance(value):
        channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    x, y = sorted([luminance(a), luminance(b)])
    return (y + 0.05) / (x + 0.05)


@pytest.mark.parametrize(
    "foreground,background",
    [
        ("#11140F", "#5590BF"),
        ("#FFFFFF", "#3978A8"),
        ("#285F89", "#FFFFFF"),
        ("#285F89", "#F6F3E9"),
        ("#43483E", "#FFFFFF"),
        ("#43483E", "#F6F3E9"),
    ],
)
def test_normal_text_contrast(foreground, background):
    assert contrast(foreground, background) >= 4.5


def test_focus_and_input_boundary_contrast():
    assert contrast("#9C5100", "#FFFFFF") >= 3
    assert contrast("#9C5100", "#F6F3E9") >= 3
    assert contrast("#74786F", "#FFFFFF") >= 3


def test_original_local_fonts_and_license():
    manifest = json.loads(Path("docs/branding-artifacts.json").read_text())
    assert manifest["license"] == "OFL-1.1"
    assert len(manifest["files"]) == 4
    for item in manifest["files"]:
        path = Path(item["file"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        assert path.read_bytes().startswith(b"wOF2")
        assert finders.find(str(path.relative_to("backend/static")))
    assert (
        "SIL OPEN FONT LICENSE Version 1.1"
        in Path("backend/static/fonts/inter/LICENSE.txt").read_text()
    )
    css = Path("backend/static/brand.css").read_text()
    assert "https://" not in css and "http://" not in css
    for weight in (400, 500, 600, 700):
        assert f"font-weight:{weight}" in css


@override_settings(SECURE_SSL_REDIRECT=False, PRIVACY_NOTICE_TEXT="Synthetischer Test")
def test_public_pages_use_deelvo_and_local_branding(client):
    for url in ("/", "/konto/anmelden/", "/konto/registrieren/"):
        response = client.get(url)
        assert response.status_code == 200
        assert b"Deelvo" in response.content
        assert b"Zirculeih" not in response.content and b"Lendry" not in response.content
        assert b"brand.css" in response.content
        assert b"fonts.googleapis" not in response.content
    response = client.get("/konto/anmelden/")
    assert response["Cache-Control"] == "no-store, private"
    assert response["Referrer-Policy"] == "same-origin"
