from accounts.authorization import require
from inventory.models import Location

from .models import Resource
from .services import resource_scope


def affected_resources(model, branch):
    key = "location_id__in" if model is Location else "categories__id__in"
    return list(Resource.objects.filter(**{key: branch}).distinct())


def check_tree_change(actor, resource_ids):
    for resource in Resource.objects.filter(pk__in=resource_ids):
        scope = resource_scope(resource)
        require(actor, "resource.manage", scope)
        if resource.published_at:
            require(actor, "resource.publish", scope)
