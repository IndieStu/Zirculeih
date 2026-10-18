import json

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Report configured Authentik readiness without contacting the provider or printing secrets."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(
                {
                    "enabled": settings.OIDC_ENABLED,
                    "credentials_present": bool(
                        settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET
                    ),
                    "callback_url": settings.PUBLIC_BASE_URL + "/konto/oidc/callback/",
                    "local_login_available": True,
                    "live_provider_verified": False,
                }
            )
        )
