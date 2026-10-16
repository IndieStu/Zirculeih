"""Compose the single visible Admin role with explicit operational grants.

Protected authority remains outside group grants. This helper is only used by
operator bootstrap and the explicit fictional review upgrade, never public input.
"""

from django.core.exceptions import PermissionDenied

from .authorization import ACTIONS, SYSTEM_ACTIONS, authorization_write, bump
from .models import Grant, Group, Membership, User
from .services import audit


def compose_admin(user_id):
    with authorization_write() as revision:
        user = User.objects.get(pk=user_id, is_active=True)
        if not user.is_system_admin:
            raise PermissionDenied
        group, _ = Group.objects.get_or_create(name=f"Admin · {user.email}")
        Membership.objects.get_or_create(user=user, group=group, removed_at=None)
        for action in ACTIONS - SYSTEM_ACTIONS:
            Grant.objects.get_or_create(group=group, action=action, effect="allow")
        audit(
            None,
            "admin.operational_access_composed",
            subject=user,
            reason="Explicit operator composition of the visible Admin role",
        )
        bump(revision)
