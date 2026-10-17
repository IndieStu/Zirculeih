from django.db import migrations

SQL = r"""
CREATE FUNCTION deelvo_bundle_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Bundle evidence is immutable' USING ERRCODE='23514'; END $$;
CREATE TRIGGER bundle_immutable BEFORE UPDATE OR DELETE ON bookings_bundlereservation
FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_immutable();
CREATE TRIGGER bundle_member_immutable BEFORE UPDATE OR DELETE ON bookings_bundlemember
FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_immutable();

CREATE FUNCTION deelvo_bundle_consistent() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE gid uuid; g bookings_bundlereservation%ROWTYPE; root bookings_booking%ROWTYPE;
        total integer; unique_resources integer; found_resources jsonb;
BEGIN
 IF TG_TABLE_NAME='bookings_bundlereservation' THEN gid:=NEW.id;
 ELSIF TG_TABLE_NAME='bookings_bundlemember' THEN gid:=NEW.reservation_id;
 ELSE SELECT reservation_id INTO gid FROM bookings_bundlemember WHERE booking_id=NEW.id;
 END IF;
 IF gid IS NULL THEN RETURN NULL; END IF;
 SELECT * INTO g FROM bookings_bundlereservation WHERE id=gid;
 SELECT * INTO root FROM bookings_booking WHERE id=g.root_id;
 SELECT count(*),count(DISTINCT b.resource_id),
 jsonb_agg(b.resource_id::text ORDER BY b.resource_id::text)
 INTO total,unique_resources,found_resources
 FROM bookings_bundlemember m JOIN bookings_booking b ON b.id=m.booking_id
 WHERE m.reservation_id=gid;
 IF total<2 OR total>20 OR unique_resources<>total OR
    total<>jsonb_array_length(g.expected_resources) OR
    found_resources<>(SELECT jsonb_agg(value ORDER BY value)
      FROM jsonb_array_elements_text(g.expected_resources)) OR
    NOT EXISTS(SELECT 1 FROM bookings_bundlemember
      WHERE reservation_id=gid AND booking_id=root.id AND required)
 THEN RAISE EXCEPTION 'Incomplete bundle reservation' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM bookings_bundlemember m JOIN bookings_booking b ON b.id=m.booking_id
    WHERE m.reservation_id=gid AND
    ((b.actor_id,b.beneficiary_id,b.start,b.timezone) IS DISTINCT FROM
     (root.actor_id,root.beneficiary_id,root.start,root.timezone) OR b."end"<root."end" OR
     (b.status='cancelled')<>(root.status='cancelled') OR
     (b.status='no_show')<>(root.status='no_show')))
 THEN RAISE EXCEPTION 'Inconsistent bundle members' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER bundle_consistent AFTER INSERT ON bookings_bundlereservation
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_consistent();
CREATE CONSTRAINT TRIGGER bundle_member_consistent AFTER INSERT ON bookings_bundlemember
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_consistent();
CREATE CONSTRAINT TRIGGER booking_bundle_consistent AFTER INSERT OR UPDATE ON bookings_booking
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_consistent();
"""

REVERSE = """
DROP TRIGGER booking_bundle_consistent ON bookings_booking;
DROP TRIGGER bundle_member_consistent ON bookings_bundlemember;
DROP TRIGGER bundle_consistent ON bookings_bundlereservation;
DROP FUNCTION deelvo_bundle_consistent();
DROP TRIGGER bundle_member_immutable ON bookings_bundlemember;
DROP TRIGGER bundle_immutable ON bookings_bundlereservation;
DROP FUNCTION deelvo_bundle_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [("bookings", "0009_bundlereservation_expected_resources")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
