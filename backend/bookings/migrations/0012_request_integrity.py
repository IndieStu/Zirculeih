from django.db import migrations

SQL = r"""
ALTER TABLE bookings_reservationrequest ADD CONSTRAINT request_shape
CHECK (expected_occurrences BETWEEN 1 AND 366 AND jsonb_typeof(resources_snapshot)='array'
 AND jsonb_array_length(resources_snapshot) BETWEEN 1 AND 20);
CREATE FUNCTION deelvo_request_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Request history is permanent' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (NEW.actor_id,NEW.beneficiary_id,NEW.resource_id,NEW.timezone,NEW.time_mode,
       NEW.rule,NEW.options,NEW.key,NEW.payload_hash,NEW.created_at,
       NEW.expected_occurrences,NEW.resources_snapshot)
      IS DISTINCT FROM
      (OLD.actor_id,OLD.beneficiary_id,OLD.resource_id,OLD.timezone,OLD.time_mode,
       OLD.rule,OLD.options,OLD.key,OLD.payload_hash,OLD.created_at,
       OLD.expected_occurrences,OLD.resources_snapshot)
      OR NEW.revision<>OLD.revision+1
      OR (OLD.status IN ('rejected','cancelled'))
      OR (OLD.status='approved' AND NEW.status<>'cancelled')
      OR (OLD.status='requested' AND
          NEW.status NOT IN ('requested','approved','rejected','cancelled'))
   THEN RAISE EXCEPTION 'Invalid request transition or identity' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.status<>'requested' AND (NEW.decided_by_id IS NULL OR NEW.decided_at IS NULL
    OR btrim(NEW.reason)='') THEN
   RAISE EXCEPTION 'Request decision requires actor, time and reason' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER request_guard BEFORE INSERT OR UPDATE OR DELETE ON bookings_reservationrequest
FOR EACH ROW EXECUTE FUNCTION deelvo_request_guard();

CREATE FUNCTION deelvo_occurrence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Occurrence history is permanent' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND
   ((NEW.request_id,NEW.position,NEW.local_start,NEW.local_end,NEW.options)
    IS DISTINCT FROM (OLD.request_id,OLD.position,OLD.local_start,OLD.local_end,OLD.options)
    OR OLD.booking_id IS NOT NULL OR NEW.booking_id IS NULL)
 THEN RAISE EXCEPTION 'Original occurrence is immutable' USING ERRCODE='23514'; END IF;
 IF (SELECT status FROM bookings_reservationrequest WHERE id=NEW.request_id)<>'requested'
 THEN RAISE EXCEPTION 'Occurrence changes require an open request' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER occurrence_guard BEFORE INSERT OR UPDATE OR DELETE ON bookings_requestoccurrence
FOR EACH ROW EXECUTE FUNCTION deelvo_occurrence_guard();
CREATE FUNCTION deelvo_request_evidence_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE state text;
BEGIN
 IF TG_OP<>'INSERT' THEN
   RAISE EXCEPTION 'Occurrence evidence is immutable' USING ERRCODE='23514';
 END IF;
 SELECT r.status INTO state FROM bookings_reservationrequest r
 JOIN bookings_requestoccurrence o ON o.request_id=r.id WHERE o.id=NEW.occurrence_id;
 IF btrim(NEW.reason)='' OR
   (TG_TABLE_NAME='bookings_requestadjustment' AND state<>'requested') OR
   (TG_TABLE_NAME='bookings_occurrenceexception' AND state<>'approved')
 THEN RAISE EXCEPTION 'Invalid occurrence exception' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='bookings_occurrenceexception' THEN
   IF NOT EXISTS(SELECT 1 FROM bookings_requestoccurrence o
      JOIN bookings_reservationrequest r ON r.id=o.request_id
      JOIN bookings_booking b ON b.id=NEW.previous_id
      WHERE o.id=NEW.occurrence_id AND b.status='cancelled'
      AND (b.beneficiary_id,b.resource_id,b.timezone)=(r.beneficiary_id,r.resource_id,r.timezone)
      AND (o.booking_id=NEW.previous_id OR EXISTS(
        SELECT 1 FROM bookings_occurrenceexception e WHERE e.occurrence_id=o.id
        AND e.replacement_id=NEW.previous_id)))
   THEN RAISE EXCEPTION 'Invalid exception chain' USING ERRCODE='23514'; END IF;
   IF NEW.replacement_id IS NOT NULL AND NOT EXISTS(
      SELECT 1 FROM bookings_booking b
      JOIN bookings_booking prior_booking ON prior_booking.id=NEW.previous_id
      WHERE b.id=NEW.replacement_id AND b.status='confirmed'
      AND (b.beneficiary_id,b.resource_id,b.timezone)=
          (prior_booking.beneficiary_id,prior_booking.resource_id,prior_booking.timezone))
   THEN RAISE EXCEPTION 'Invalid replacement booking' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER request_adjustment_guard BEFORE INSERT OR UPDATE OR DELETE
ON bookings_requestadjustment FOR EACH ROW EXECUTE FUNCTION deelvo_request_evidence_guard();
CREATE TRIGGER occurrence_exception_guard BEFORE INSERT OR UPDATE OR DELETE
ON bookings_occurrenceexception FOR EACH ROW EXECUTE FUNCTION deelvo_request_evidence_guard();

CREATE FUNCTION deelvo_request_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid; r bookings_reservationrequest%ROWTYPE; n integer;
BEGIN
 IF TG_TABLE_NAME='bookings_reservationrequest' THEN rid:=NEW.id;
 ELSIF TG_TABLE_NAME='bookings_requestoccurrence' THEN rid:=NEW.request_id;
 ELSE SELECT request_id INTO rid FROM bookings_requestoccurrence WHERE id=NEW.occurrence_id;
 END IF;
 SELECT * INTO r FROM bookings_reservationrequest WHERE id=rid;
 SELECT count(*) INTO n FROM bookings_requestoccurrence WHERE request_id=rid;
 IF n<>r.expected_occurrences OR EXISTS(SELECT 1 FROM bookings_requestoccurrence
     WHERE request_id=rid AND position>=r.expected_occurrences)
 THEN RAISE EXCEPTION 'Incomplete request occurrences' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM bookings_requestoccurrence o
   LEFT JOIN bookings_booking b ON b.id=o.booking_id
   WHERE o.request_id=rid AND
    ((o.booking_id IS NOT NULL AND
      ((b.beneficiary_id,b.resource_id,b.timezone) IS DISTINCT FROM
       (r.beneficiary_id,r.resource_id,r.timezone))) OR
     (r.status IN ('requested','rejected') AND o.booking_id IS NOT NULL) OR
     (r.status='approved' AND o.booking_id IS NULL AND NOT COALESCE(
       (SELECT cancelled FROM bookings_requestadjustment a WHERE a.occurrence_id=o.id
        ORDER BY revision DESC LIMIT 1),false))))
 THEN RAISE EXCEPTION 'Request and bookings disagree' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER request_consistent AFTER INSERT OR UPDATE ON bookings_reservationrequest
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_request_consistent();
CREATE CONSTRAINT TRIGGER occurrence_request_consistent AFTER INSERT OR UPDATE
ON bookings_requestoccurrence DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION deelvo_request_consistent();
CREATE CONSTRAINT TRIGGER adjustment_request_consistent AFTER INSERT
ON bookings_requestadjustment DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION deelvo_request_consistent();
"""


class Migration(migrations.Migration):
    dependencies = [("bookings", "0011_occurrenceexception_requestadjustment_and_more")]
    operations = [migrations.RunSQL(SQL)]
