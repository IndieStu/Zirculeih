from accounts.authorization import allowed
from inventory.services import Resolution, asset_scope

from .models import ResourceUnit
from .services import resource_scope


def project_identifier(actor, identifier):
    unit = (
        identifier.unit
        if identifier.unit_id
        else ResourceUnit.objects.filter(asset_id=identifier.asset_id, is_active=True)
        .select_related("resource__location")
        .first()
    )
    asset = identifier.asset if identifier.asset_id else (unit.asset if unit else None)
    if identifier.unit_id and (
        not unit.is_active
        or unit.resource.archived_at
        or not allowed(actor, "identifier.resolve", resource_scope(unit.resource))
    ):
        return Resolution("unknown")
    if asset and not allowed(actor, "identifier.resolve", asset_scope(asset)):
        return Resolution("unknown")
    if asset is None and unit is None:
        return Resolution("unknown")
    show_unit = (
        unit
        and not unit.resource.archived_at
        and allowed(actor, "identifier.resolve", resource_scope(unit.resource))
    )
    return Resolution(
        "found",
        asset.pk if asset else None,
        asset.name if asset else unit.name,
        asset.inventory_number if asset else "",
        unit.pk if show_unit else None,
        unit.resource_id if show_unit else None,
        unit.resource.title if show_unit else "",
    )
