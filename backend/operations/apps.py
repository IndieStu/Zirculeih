from django.apps import AppConfig


class OperationsConfig(AppConfig):
    name = "operations"

    def ready(self):
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        from . import checks  # noqa: F401

        failures = checks.configuration_problems(settings)
        if failures:
            profile = "production" if settings.DEPLOYMENT_PROFILE == "production" else "deployment"
            raise ImproperlyConfigured(
                "Unsafe " + profile + " configuration: " + ", ".join(code for code, _ in failures)
            )
