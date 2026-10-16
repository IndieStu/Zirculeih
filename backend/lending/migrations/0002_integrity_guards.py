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
       OR (OLD.status IN ('completed','cancelled') AND NEW.status<>OLD.status)
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
CREATE OR REPLACE FUNCTION deelvo_claim_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE booking_row bookings_booking%ROWTYPE;
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Claims retain history' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND
     ((NEW.booking_id,NEW.unit_id) IS DISTINCT FROM
      (OLD.booking_id,OLD.unit_id) OR (NOT OLD.is_active AND NEW.is_active)) THEN
    RAISE EXCEPTION 'Claim identity is immutable' USING ERRCODE='23514';
  END IF;
  SELECT * INTO booking_row FROM bookings_booking WHERE id=NEW.booking_id;
  IF NEW.unit_id IS DISTINCT FROM booking_row.unit_id OR
     lower(NEW.during)>booking_row.start OR upper(NEW.during)<booking_row."end" THEN
    RAISE EXCEPTION 'Claim does not cover its booking' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' AND NEW.during IS DISTINCT FROM OLD.during THEN
    IF lower(NEW.during)<>lower(OLD.during) OR upper(NEW.during)<=upper(OLD.during)
      OR NOT EXISTS (SELECT 1 FROM lending_extension WHERE booking_id=NEW.booking_id
        AND booking_revision=booking_row.revision AND after_end=booking_row."end")
      OR upper(NEW.during)<>booking_row."end" +
        make_interval(mins => (booking_row.policy_snapshot->>'buffer_after_minutes')::int) THEN
      RAISE EXCEPTION 'Claim changes require a matching extension' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION deelvo_lending_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Permanent lending evidence' USING ERRCODE='23514'; END $$;
CREATE TRIGGER acceptance_immutable BEFORE UPDATE OR DELETE ON lending_acceptance
FOR EACH ROW EXECUTE FUNCTION deelvo_lending_immutable();
CREATE TRIGGER identity_check_immutable BEFORE UPDATE OR DELETE ON lending_identitycheck
FOR EACH ROW EXECUTE FUNCTION deelvo_lending_immutable();
CREATE TRIGGER extension_immutable BEFORE UPDATE OR DELETE ON lending_extension
FOR EACH ROW EXECUTE FUNCTION deelvo_lending_immutable();
CREATE TRIGGER operation_immutable BEFORE UPDATE OR DELETE ON lending_operation
FOR EACH ROW EXECUTE FUNCTION deelvo_lending_immutable();
CREATE FUNCTION deelvo_agreement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' OR OLD.published_at IS NOT NULL THEN
  RAISE EXCEPTION 'Published text remains immutable' USING ERRCODE='23514';
 END IF;
 IF (NEW.agreement_id,NEW.number,NEW.text,NEW.created_by_id) IS DISTINCT FROM
    (OLD.agreement_id,OLD.number,OLD.text,OLD.created_by_id) THEN
  RAISE EXCEPTION 'Create a new text version' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER agreement_version_guard BEFORE UPDATE OR DELETE ON lending_agreementversion
FOR EACH ROW EXECUTE FUNCTION deelvo_agreement_guard();
CREATE FUNCTION deelvo_loan_line_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE b bookings_booking%ROWTYPE; a uuid; borrower uuid;
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Loan history is permanent' USING ERRCODE='23514'; END IF;
 SELECT * INTO b FROM bookings_booking WHERE id=NEW.booking_id;
 SELECT asset_id INTO a FROM resources_resourceunit WHERE id=NEW.unit_id;
 SELECT borrower_id INTO borrower FROM lending_loan WHERE id=NEW.loan_id;
 IF NEW.unit_id IS DISTINCT FROM b.unit_id OR NEW.asset_id IS DISTINCT FROM a
  OR borrower IS DISTINCT FROM b.beneficiary_id 
  OR b.policy_snapshot->>'use_mode'<>'physical_loan' THEN
  RAISE EXCEPTION 'Loan identity mismatch' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND ((NEW.loan_id,NEW.booking_id,NEW.unit_id,NEW.asset_id,
    NEW.issue_condition,NEW.accessories)
   IS DISTINCT FROM (OLD.loan_id,OLD.booking_id,OLD.unit_id,OLD.asset_id,
    OLD.issue_condition,OLD.accessories)
   OR OLD.returned_at IS NOT NULL) THEN
  RAISE EXCEPTION 'Loan identity or return is immutable' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND NEW.expected_return<>OLD.expected_return AND NOT EXISTS
  (SELECT 1 FROM lending_extension WHERE booking_id=NEW.booking_id 
     AND after_end>=NEW.expected_return
    AND booking_revision=b.revision) THEN
  RAISE EXCEPTION 'Due changes require extension' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loan_line_guard BEFORE INSERT OR UPDATE OR DELETE ON lending_loanline
FOR EACH ROW EXECUTE FUNCTION deelvo_loan_line_guard();
CREATE FUNCTION deelvo_custody_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; line lending_loanline%ROWTYPE; state text;
BEGIN
 IF TG_TABLE_NAME='bookings_booking' THEN target:=NEW.id; ELSE target:=NEW.booking_id; END IF;
 SELECT * INTO line FROM lending_loanline WHERE booking_id=target;
 IF NOT FOUND THEN RETURN NULL; END IF;
 SELECT status INTO state FROM bookings_booking WHERE id=target;
 IF (line.returned_at IS NULL AND state<>'active') OR
    (line.returned_at IS NOT NULL AND state<>'completed') THEN
  RAISE EXCEPTION 'Custody and booking lifecycle inconsistent' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER custody_booking_consistent AFTER INSERT OR UPDATE ON lending_loanline
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_custody_consistent();
CREATE CONSTRAINT TRIGGER booking_custody_consistent AFTER INSERT OR UPDATE ON bookings_booking
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_custody_consistent();
CREATE FUNCTION deelvo_loan_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Loan history is permanent' USING ERRCODE='23514'; END IF;
 IF (NEW.borrower_id,NEW.actor_id,NEW.issued_at,NEW.evidence) IS DISTINCT FROM
    (OLD.borrower_id,OLD.actor_id,OLD.issued_at,OLD.evidence) OR OLD.closed_at IS NOT NULL THEN
  RAISE EXCEPTION 'Loan evidence is immutable' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER loan_guard BEFORE UPDATE OR DELETE ON lending_loan
FOR EACH ROW EXECUTE FUNCTION deelvo_loan_guard();

"""


class Migration(migrations.Migration):
    dependencies = [("lending", "0001_initial")]
    operations = [migrations.RunSQL(SQL)]
