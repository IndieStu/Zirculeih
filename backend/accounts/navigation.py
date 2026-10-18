from inventory.views import any_action

from accounts.authorization import allowed


def operational_user(user):
    return getattr(user, "is_authenticated", False) and (
        allowed(user, "permissions.manage")
        or any(
            any_action(user, action)
            for action in (
                "asset.read",
                "resource.manage",
                "booking.read_all",
                "booking.approve",
                "booking.configure",
                "booking.configure",
                "loan.read",
                "loan.checkout",
                "loan.return",
                "user.invite",
                "qualification.issue",
            )
        )
    )


def navigation(request):
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return {}
    flags = {
        "staff_navigation": operational_user(user),
        "assetops_navigation": any_action(user, "inventory_run.read")
        or any_action(user, "inventory_run.create"),
        "maintenance_navigation": any_action(user, "maintenance.manage"),
        "inventory_read_navigation": any_action(user, "asset.read"),
        "lookup_navigation": any_action(user, "identifier.resolve"),
        "people_navigation": allowed(user, "user.invite"),
        "group_navigation": allowed(user, "permissions.manage")
        or any_action(user, "user.manage_groups"),
        "category_navigation": any_action(user, "category.manage"),
        "location_navigation": any_action(user, "location.read")
        or any_action(user, "location.manage"),
        "hours_navigation": any_action(user, "booking.configure"),
        "qualification_navigation": any_action(user, "qualification.issue")
        or any_action(user, "booking.configure"),
    }
    flags["sidebar_navigation"] = (
        flags["staff_navigation"]
        and (
            not request.path.startswith("/entdecken/")
            or request.path.startswith("/entdecken/verwaltung/")
        )
        and request.path != "/"
    )
    return flags
