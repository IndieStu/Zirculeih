from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION deelvo_custody_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target uuid; line lending_loanline%ROWTYPE; state text; mode text;
BEGIN
 IF TG_TABLE_NAME='bookings_booking' THEN target:=NEW.id; ELSE target:=NEW.booking_id; END IF;
 SELECT * INTO line FROM lending_loanline WHERE booking_id=target;
 IF NOT FOUND THEN
  SELECT status,policy_snapshot->>'use_mode' INTO state,mode FROM bookings_booking WHERE id=target;
  IF mode='physical_loan' AND state IN ('active','completed') THEN
   RAISE EXCEPTION 'Physical lifecycle requires actual loan evidence' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
 END IF;
 SELECT status INTO state FROM bookings_booking WHERE id=target;
 IF (line.returned_at IS NULL AND state<>'active') OR
    (line.returned_at IS NOT NULL AND state<>'completed') THEN
  RAISE EXCEPTION 'Custody and booking lifecycle inconsistent' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [("lending", "0004_no_show_terminal_guard")]
    operations = [migrations.RunSQL(SQL)]
