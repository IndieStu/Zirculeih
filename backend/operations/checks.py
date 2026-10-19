from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Tags, register


def configuration_problems(config):
    problems = []
    if config.DEPLOYMENT_PROFILE not in {"development", "production", "restore"}:
        problems.append(("E001", "Unknown deployment profile."))
    if config.DEPLOYMENT_PROFILE == "restore" and not config.RESTORE_MODE:
        problems.append(("E002", "Restore profile requires DEELVO_RESTORE_MODE=true."))
    if config.DEPLOYMENT_PROFILE != "production":
        return problems
    conditions = [
        ("E010", not config.DEBUG, "Production requires DEBUG=false."),
        (
            "E011",
            not config.REVIEW_MODE and not config.RESTORE_MODE,
            "Review/restore is not production.",
        ),
        ("E012", config.SECURE_SSL_REDIRECT, "Production requires HTTPS redirect."),
        (
            "E013",
            config.SESSION_COOKIE_SECURE and config.CSRF_COOKIE_SECURE,
            "Secure cookies required.",
        ),
        ("E014", config.SECURE_HSTS_SECONDS > 0, "Enable HSTS after verified TLS."),
        (
            "E015",
            bool(config.PRIVACY_NOTICE_TEXT)
            and config.PRIVACY_NOTICE_VERSION not in {"", "unconfigured"},
            "Organization privacy notice/version required.",
        ),
        (
            "E016",
            config.OIDC_ENABLED,
            "Configure required staff Authentik login before production.",
        ),
        (
            "E017",
            bool(config.ALLOWED_HOSTS)
            and all(
                h not in {"*", "localhost", "127.0.0.1", "[::1]"} and not h.startswith(".")
                for h in config.ALLOWED_HOSTS
            ),
            "Explicit production hosts required.",
        ),
    ]
    parsed = urlsplit(config.PUBLIC_BASE_URL)
    conditions.append(
        (
            "E018",
            parsed.scheme == "https"
            and parsed.hostname in config.ALLOWED_HOSTS
            and not parsed.username
            and not parsed.query
            and not parsed.fragment
            and parsed.path in {"", "/"},
            "Fixed HTTPS public origin matching allowed hosts required.",
        )
    )
    for code, passes, message in conditions:
        if not passes:
            problems.append((code, message))
    return problems


@register(Tags.security)
def deployment_checks(app_configs, **kwargs):
    return [
        Error(message, id="deelvo." + code) for code, message in configuration_problems(settings)
    ]
