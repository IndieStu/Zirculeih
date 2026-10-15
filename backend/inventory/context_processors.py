def navigation(request):
    if not request.user.is_authenticated:
        return {}
    from .views import any_action

    return {
        "inventory_navigation": any(
            any_action(request.user, action)
            for action in (
                "asset.read",
                "asset.manage",
                "identifier.resolve",
                "location.manage",
                "category.manage",
                "identifier.namespace_manage",
                "custom_field.manage",
            )
        )
    }
