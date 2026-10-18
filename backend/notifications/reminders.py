from datetime import timedelta

from accounts.authorization import authorization_write
from bookings.models import Booking
from django.urls import reverse
from django.utils import timezone
from lending.models import LoanLine

from .services import absolute, configuration, enqueue


def schedule():
    with authorization_write():
        config, now = configuration(), timezone.now()
        created = 0
        for booking in Booking.objects.filter(
            status="confirmed",
            appointment__pickup_at__gt=now,
            appointment__pickup_at__lte=now + timedelta(hours=config.pickup_hours),
        ).select_related("appointment", "beneficiary"):
            moment = booking.appointment.pickup_at
            key = f"pickup:{booking.pk}:{moment.isoformat()}"
            enqueue(
                booking.beneficiary,
                "pickup",
                key,
                booking=booking,
                url=absolute(reverse("booking_detail", args=[booking.pk])),
                when=timezone.localtime(moment).strftime("%d.%m.%Y %H:%M %Z"),
                context={"moment": moment.isoformat()},
            )
            created += 1
        for line in LoanLine.objects.filter(
            returned_at=None, expected_return__lte=now + timedelta(hours=config.return_hours)
        ).select_related("loan__borrower", "booking"):
            due = line.expected_return
            overdue = due <= now
            kind = "overdue" if overdue else "return"
            bucket = (
                int((now - due).total_seconds() // (config.overdue_repeat_hours * 3600))
                if overdue
                else 0
            )
            enqueue(
                line.loan.borrower,
                kind,
                f"{kind}:{line.pk}:{due.isoformat()}:{bucket}",
                booking=line.booking,
                url=absolute(reverse("loan_detail", args=[line.loan_id])),
                when=timezone.localtime(due).strftime("%d.%m.%Y %H:%M %Z"),
                context={"moment": due.isoformat(), "bucket": bucket},
            )
            created += 1
        return created
