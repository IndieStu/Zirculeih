from django.db import migrations

SQL = r"""
CREATE FUNCTION deelvo_loan_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; closed timestamptz; issued timestamptz; has_open boolean;
BEGIN
 IF TG_TABLE_NAME='lending_loan' THEN target:=NEW.id; ELSE target:=NEW.loan_id; END IF;
 SELECT closed_at,issued_at INTO closed,issued FROM lending_loan WHERE id=target;
 IF NOT EXISTS (SELECT 1 FROM lending_loanline WHERE loan_id=target) THEN
  RAISE EXCEPTION 'A loan needs actual lines' USING ERRCODE='23514';
 END IF;
 SELECT EXISTS(SELECT 1 FROM lending_loanline WHERE loan_id=target AND returned_at IS NULL)
 INTO has_open;
 IF (closed IS NULL)<>has_open OR closed<issued THEN
  RAISE EXCEPTION 'Loan closure must match actual returns' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER loan_receipt_consistent AFTER INSERT OR UPDATE ON lending_loan
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_loan_consistent();
CREATE CONSTRAINT TRIGGER line_receipt_consistent AFTER INSERT OR UPDATE ON lending_loanline
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_loan_consistent();
CREATE FUNCTION deelvo_appointment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rev integer;
BEGIN
 IF TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Appointment history is permanent' USING ERRCODE='23514';
 END IF;
 SELECT revision INTO rev FROM bookings_booking WHERE id=NEW.booking_id;
 IF (NEW.booking_id,NEW.pickup_at) IS DISTINCT FROM (OLD.booking_id,OLD.pickup_at)
  OR NOT EXISTS (SELECT 1 FROM lending_extension WHERE booking_id=NEW.booking_id
    AND booking_revision=rev AND after_end>=NEW.return_at) THEN
  RAISE EXCEPTION 'Appointment change needs extension evidence' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER appointment_guard BEFORE UPDATE OR DELETE ON lending_appointment
FOR EACH ROW EXECUTE FUNCTION deelvo_appointment_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("lending", "0002_integrity_guards")]
    operations = [migrations.RunSQL(SQL)]
