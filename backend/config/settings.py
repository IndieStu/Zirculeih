"""Deelvo settings: PostgreSQL, local accounts and configured Authentik integration."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value


def flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, str(default)).lower()
    if raw not in {"true", "false"}:
        raise ImproperlyConfigured(f"{name} must be true or false")
    return raw == "true"


SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must contain at least 50 characters")
DEBUG = flag("DJANGO_DEBUG")
ALLOWED_HOSTS = [s.strip() for s in required("DJANGO_ALLOWED_HOSTS").split(",") if s.strip()]
CSRF_TRUSTED_ORIGINS = [
    s.strip() for s in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if s.strip()
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
]
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/konto/anmelden/"
LOGIN_REDIRECT_URL = "/konto/"
LOGOUT_REDIRECT_URL = "/"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
PRIVACY_NOTICE_TEXT = os.environ.get("PRIVACY_NOTICE_TEXT", "")
PRIVACY_NOTICE_VERSION = os.environ.get("PRIVACY_NOTICE_VERSION", "unconfigured")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = flag("EMAIL_USE_TLS")
EMAIL_USE_SSL = flag("EMAIL_USE_SSL")
EMAIL_TIMEOUT = 5
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@localhost")
OIDC_ENABLED = flag("OIDC_ENABLED")
OIDC_ISSUER = os.environ.get("OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")
OIDC_AUTHORIZATION_ENDPOINT = os.environ.get("OIDC_AUTHORIZATION_ENDPOINT", "")
OIDC_TOKEN_ENDPOINT = os.environ.get("OIDC_TOKEN_ENDPOINT", "")
OIDC_JWKS_ENDPOINT = os.environ.get("OIDC_JWKS_ENDPOINT", "")

MIDDLEWARE = [
    "config.middleware.RequestLogMiddleware",
    "config.middleware.AccountPrivacyMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required("POSTGRES_DB"),
        "USER": required("POSTGRES_USER"),
        "PASSWORD": required("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
    }
}
LANGUAGE_CODE = "de-de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_SSL_REDIRECT = flag("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
X_FRAME_OPTIONS = "DENY"
# Enable only behind a proxy that strips client-supplied X-Forwarded-Proto.
if flag("DJANGO_TRUST_PROXY"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^health/live/$", r"^health/ready/$"]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "config.logging.JsonFormatter"}},
    "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["stdout"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        "gunicorn.error": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
    },
}

# Explicit local HTTP configuration uses matching cookies; deployed HTTPS keeps Secure.
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT or PUBLIC_BASE_URL.startswith("https://")
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
if PRIVACY_NOTICE_TEXT and not PRIVACY_NOTICE_VERSION.strip():
    raise ImproperlyConfigured("A configured privacy notice requires a non-empty version")
if OIDC_ENABLED:
    from urllib.parse import urlsplit

    for oidc_value in (
        OIDC_ISSUER,
        OIDC_AUTHORIZATION_ENDPOINT,
        OIDC_TOKEN_ENDPOINT,
        OIDC_JWKS_ENDPOINT,
        PUBLIC_BASE_URL,
    ):
        parsed = urlsplit(oidc_value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.fragment:
            raise ImproperlyConfigured(
                "OIDC endpoints and PUBLIC_BASE_URL require fixed HTTPS URLs"
            )
    if not OIDC_CLIENT_ID or not OIDC_CLIENT_SECRET:
        raise ImproperlyConfigured("OIDC client credentials required when enabled")
