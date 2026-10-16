from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION deelvo_booking_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent uuid;
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Bookings retain history' USING ERRCODE='23514';
  END IF;
  SELECT resource_id INTO parent FROM resources_resourceunit WHERE id=NEW.unit_id;
  IF parent IS DISTINCT FROM NEW.resource_id THEN
    RAISE EXCEPTION 'Booking resource/unit mismatch' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' THEN
    IF (NEW.actor_id,NEW.beneficiary_id,NEW.resource_id,NEW.unit_id,NEW.start,
        NEW.start_date,NEW.timezone,NEW.policy_snapshot)
       IS DISTINCT FROM
       (OLD.actor_id,OLD.beneficiary_id,OLD.resource_id,OLD.unit_id,OLD.start,
        OLD.start_date,OLD.timezone,OLD.policy_snapshot)
       OR (OLD.status IN ('completed','cancelled','no_show') AND NEW.status<>OLD.status)
       OR (OLD.status='active' AND NEW.status='confirmed') THEN
      RAISE EXCEPTION 'Booking identity or terminal state is immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  IF TG_OP='UPDATE' AND (NEW."end",NEW.end_date_exclusive) IS DISTINCT FROM
    (OLD."end",OLD.end_date_exclusive) THEN
    IF NOT EXISTS (SELECT 1 FROM lending_extension WHERE booking_id=NEW.id
      AND before_end=OLD."end" AND after_end=NEW."end"
      AND before_date IS NOT DISTINCT FROM OLD.end_date_exclusive
      AND after_date IS NOT DISTINCT FROM NEW.end_date_exclusive
      AND booking_revision=NEW.revision AND NEW.revision=OLD.revision+1)
      OR OLD.status NOT IN ('confirmed','active') THEN
      RAISE EXCEPTION 'End changes require an immutable extension' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("lending", "0003_receipt_consistency"),
        ("bookings", "0004_remove_booking_booking_status_valid_and_more"),
    ]
    operations = [migrations.RunSQL(SQL)]
