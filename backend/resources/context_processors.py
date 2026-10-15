def navigation(request):
    if not request.user.is_authenticated:
        return {}
    from inventory.views import any_action

    return {
        "resource_navigation": any_action(request.user, "resource.manage")
        or any_action(request.user, "resource.type_manage")
    }
