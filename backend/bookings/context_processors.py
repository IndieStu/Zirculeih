def navigation(request):
    if (
        not request.user.is_authenticated
        or not request.user.is_active
        or not request.user.email_verified_at
    ):
        return {}
    from inventory.views import any_action

    return {
        "personal_bookings_navigation": True,
        "loan_navigation": any(
            any_action(request.user, a) for a in ("loan.read", "loan.checkout", "loan.return")
        ),
        "agreement_navigation": any_action(request.user, "agreement.edit"),
        "booking_navigation": any(
            any_action(request.user, a)
            for a in ("booking.read_all", "booking.configure", "booking.block")
        ),
    }
