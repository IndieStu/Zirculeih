from django.db import migrations

SQL = """
CREATE FUNCTION deelvo_transition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE candidate bookings_allocationclaim%ROWTYPE; promise bookings_booking%ROWTYPE;
        rule bookings_bookingpolicy%ROWTYPE; lo timestamptz; hi timestamptz;
BEGIN
  SELECT * INTO candidate FROM bookings_allocationclaim WHERE id=NEW.id;
  IF NOT candidate.is_active THEN RETURN NULL; END IF;
  PERFORM 1 FROM resources_resourceunit WHERE id=candidate.unit_id FOR UPDATE;
  SELECT * INTO promise FROM bookings_booking WHERE id=candidate.booking_id;
  SELECT * INTO rule FROM bookings_bookingpolicy WHERE resource_id=promise.resource_id;
  lo := LEAST(lower(candidate.during),
      promise.start - make_interval(mins => rule.buffer_before_minutes));
  hi := GREATEST(upper(candidate.during),
      promise."end" + make_interval(mins => rule.buffer_after_minutes));
  IF EXISTS (
    SELECT 1 FROM bookings_allocationclaim other
    JOIN bookings_booking b ON b.id=other.booking_id
    WHERE other.unit_id=candidate.unit_id AND other.id<>candidate.id
      AND (other.is_active OR
        (b.status='completed' AND b.policy_snapshot->>'use_mode'='onsite'))
      AND LEAST(lower(other.during),
        b.start - make_interval(mins => rule.buffer_before_minutes)) < hi
      AND GREATEST(upper(other.during),
        b."end" + make_interval(mins => rule.buffer_after_minutes)) > lo
  ) THEN
    RAISE EXCEPTION 'Booking transition conflict' USING ERRCODE='23P01';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER booking_transition_integrity
AFTER INSERT OR UPDATE ON bookings_allocationclaim
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.is_active)
EXECUTE FUNCTION deelvo_transition_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("bookings", "0006_alter_schedulewindow_weekday")]
    operations = [
        migrations.RunSQL(
            SQL,
            "DROP TRIGGER booking_transition_integrity ON bookings_allocationclaim; "
            "DROP FUNCTION deelvo_transition_guard();",
        )
    ]
