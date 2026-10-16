from django.db import migrations

SQL = r"""
ALTER TABLE bookings_allocationclaim ADD CONSTRAINT claim_bounded_half_open
CHECK (NOT isempty(during) AND lower(during) IS NOT NULL AND upper(during) IS NOT NULL
       AND lower_inc(during) AND NOT upper_inc(during));
CREATE FUNCTION deelvo_booking_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
    IF (NEW.actor_id,NEW.beneficiary_id,NEW.resource_id,NEW.unit_id,NEW.start,NEW."end",
        NEW.start_date,NEW.end_date_exclusive,NEW.timezone,NEW.policy_snapshot)
       IS DISTINCT FROM
       (OLD.actor_id,OLD.beneficiary_id,OLD.resource_id,OLD.unit_id,OLD.start,OLD."end",
        OLD.start_date,OLD.end_date_exclusive,OLD.timezone,OLD.policy_snapshot)
       OR (OLD.status IN ('completed','cancelled') AND NEW.status<>OLD.status)
       OR (OLD.status='active' AND NEW.status='confirmed') THEN
      RAISE EXCEPTION 'Booking identity or terminal state is immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER booking_identity BEFORE INSERT OR UPDATE OR DELETE ON bookings_booking
FOR EACH ROW EXECUTE FUNCTION deelvo_booking_guard();
CREATE FUNCTION deelvo_claim_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE booking_row bookings_booking%ROWTYPE;
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Claims retain history' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND
     ((NEW.booking_id,NEW.unit_id,NEW.during) IS DISTINCT FROM
      (OLD.booking_id,OLD.unit_id,OLD.during) OR (NOT OLD.is_active AND NEW.is_active)) THEN
    RAISE EXCEPTION 'Claim identity is immutable' USING ERRCODE='23514';
  END IF;
  SELECT * INTO booking_row FROM bookings_booking WHERE id=NEW.booking_id;
  IF NEW.unit_id IS DISTINCT FROM booking_row.unit_id OR
     lower(NEW.during)>booking_row.start OR upper(NEW.during)<booking_row."end" THEN
    RAISE EXCEPTION 'Claim does not cover its booking' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER claim_identity BEFORE INSERT OR UPDATE OR DELETE ON bookings_allocationclaim
FOR EACH ROW EXECUTE FUNCTION deelvo_claim_guard();
CREATE FUNCTION deelvo_booking_claim_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; state text; active_claim boolean;
BEGIN
  IF TG_TABLE_NAME='bookings_booking' THEN target := NEW.id;
  ELSE target := NEW.booking_id; END IF;
  SELECT status INTO state FROM bookings_booking WHERE id=target;
  SELECT is_active INTO active_claim FROM bookings_allocationclaim WHERE booking_id=target;
  IF active_claim IS NULL OR active_claim<>(state IN ('confirmed','active')) THEN
    RAISE EXCEPTION 'Booking and claim must commit consistently' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER booking_claim_consistent AFTER INSERT OR UPDATE ON bookings_booking
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_booking_claim_consistent();
CREATE CONSTRAINT TRIGGER claim_booking_consistent
AFTER INSERT OR UPDATE ON bookings_allocationclaim
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_booking_claim_consistent();
"""
REVERSE = """
DROP TRIGGER claim_booking_consistent ON bookings_allocationclaim;
DROP TRIGGER booking_claim_consistent ON bookings_booking;
DROP FUNCTION deelvo_booking_claim_consistent();
DROP TRIGGER claim_identity ON bookings_allocationclaim;
DROP FUNCTION deelvo_claim_guard();
DROP TRIGGER booking_identity ON bookings_booking;
DROP FUNCTION deelvo_booking_guard();
ALTER TABLE bookings_allocationclaim DROP CONSTRAINT claim_bounded_half_open;
"""


class Migration(migrations.Migration):
    dependencies = [("bookings", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
