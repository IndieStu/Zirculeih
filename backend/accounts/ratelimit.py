import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import RateBucket


def take(request, action, identity="", limit=10):
    # REMOTE_ADDR only: no trust in client-supplied forwarding headers.
    keys = [f"ip:{request.META.get('REMOTE_ADDR', '')}:{action}"]
    if identity:
        keys.append(f"identity:{identity.strip().lower()}:{action}")
    for value in keys:
        digest = hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()
        with transaction.atomic():
            bucket, _ = RateBucket.objects.get_or_create(
                key=digest, defaults={"expires_at": timezone.now() + timedelta(minutes=15)}
            )
            bucket = RateBucket.objects.select_for_update().get(pk=bucket.pk)
            if bucket.expires_at <= timezone.now():
                bucket.count = 0
                bucket.expires_at = timezone.now() + timedelta(minutes=15)
            if bucket.count >= limit:
                return False
            bucket.count += 1
            bucket.save()
    return True
