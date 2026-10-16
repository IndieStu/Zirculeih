"""Generate private review configuration explicitly, never overwrite an existing file."""

import argparse
import ipaddress
import re
import secrets
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument(
    "--url", required=True, help="Private review URL, including port for direct HTTP"
)
parser.add_argument("--bind", default="127.0.0.1", help="Loopback or this host's Tailscale IPv4")
parser.add_argument("--port", type=int, default=8766)
parser.add_argument("--build", required=True, help="Checked-out Git SHA")
args = parser.parse_args()
url = urlsplit(args.url)
if (
    url.scheme not in {"http", "https"}
    or not url.hostname
    or url.username
    or url.password
    or url.path not in {"", "/"}
    or url.query
    or url.fragment
):
    parser.error("Use a fixed http(s) origin without credentials/path/query")
if not re.fullmatch(r"[a-zA-Z0-9.-]+", url.hostname):
    parser.error("Use a plain private hostname or IPv4")
bind = ipaddress.ip_address(args.bind)
if bind.version != 4 or not (bind.is_loopback or bind in ipaddress.ip_network("100.64.0.0/10")):
    parser.error("Bind must be loopback or a Tailscale 100.64.0.0/10 IPv4, never wildcard/public")
if not re.fullmatch(r"[0-9a-f]{7,40}", args.build) or not 1024 <= args.port <= 65535:
    parser.error("Valid Git SHA and port 1024–65535 required")
if url.scheme == "http" and (url.port or 80) != args.port:
    parser.error("Direct HTTP URL port must match --port; use HTTPS for the proxy example")
origin = args.url.rstrip("/")
secure = url.scheme == "https"
path = Path(".env.review")
values = {
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
    "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
    "POSTGRES_DB": "deelvo_review",
    "POSTGRES_USER": "deelvo_review",
    "POSTGRES_HOST": "db",
    "POSTGRES_PORT": "5432",
    "DJANGO_ALLOWED_HOSTS": f"{url.hostname},localhost,127.0.0.1",
    "DJANGO_DEBUG": "false",
    "DJANGO_SECURE_SSL_REDIRECT": str(secure).lower(),
    "DJANGO_TRUST_PROXY": str(secure).lower(),
    "DJANGO_HSTS_SECONDS": "0",
    "DJANGO_CSRF_TRUSTED_ORIGINS": origin,
    "PUBLIC_BASE_URL": origin,
    "OIDC_ENABLED": "false",
    "DEELVO_REVIEW_MODE": "true",
    "DEELVO_REVIEW_BUILD": args.build,
    "REVIEW_BIND_IP": str(bind),
    "REVIEW_PORT": str(args.port),
    "REVIEW_EMAIL_DIR": "/app/review-mail",
    "DEFAULT_FROM_EMAIL": "review@deelvo.example.test",
    "PRIVACY_NOTICE_VERSION": "fictional-review-v1",
    ("PRIVACY_NOTICE_TEXT"): (
        "UX-Testinstanz. Ausschließlich fiktive Konten und Testdaten "
        "verwenden. E-Mails werden nur lokal erfasst."
    ),
}
try:
    with path.open("x") as stream:
        path.chmod(0o600)
        stream.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
except FileExistsError:
    parser.error(".env.review exists; refusing to overwrite")
print("Created private .env.review; no password printed")
