from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("bookings", "0002_integrity_guards")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE bookings_allocationclaim ADD CONSTRAINT claim_finite_bounds "
            "CHECK (isfinite(lower(during)) AND isfinite(upper(during)))",
            "ALTER TABLE bookings_allocationclaim DROP CONSTRAINT claim_finite_bounds",
        )
    ]
