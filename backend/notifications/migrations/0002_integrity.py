from django.db import migrations

SQL = r"""
CREATE FUNCTION deelvo_delivery_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Delivery keys retain idempotency history' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' THEN
   IF (NEW.id,NEW.user_id,NEW.key,NEW.kind,NEW.booking_id,NEW.request_id,
       NEW.action_token_digest,NEW.created_at) IS DISTINCT FROM
      (OLD.id,OLD.user_id,OLD.key,OLD.kind,OLD.booking_id,OLD.request_id,
       OLD.action_token_digest,OLD.created_at) OR
      (NEW.payload IS DISTINCT FROM OLD.payload AND NOT
        (octet_length(NEW.payload)=0 AND OLD.status IN ('sent','skipped','failed'))) OR
      (OLD.status IN ('sent','skipped') AND NEW.status<>OLD.status)
   THEN RAISE EXCEPTION 'Delivery envelope is immutable' USING ERRCODE='23514'; END IF;
 END IF;
 IF NOT ((NEW.status='sending' AND NEW.lease_id IS NOT NULL AND NEW.lease_until IS NOT NULL)
     OR (NEW.status<>'sending' AND NEW.lease_id IS NULL AND NEW.lease_until IS NULL))
 THEN RAISE EXCEPTION 'Sending requires an exclusive delivery lease' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER delivery_guard BEFORE INSERT OR UPDATE OR DELETE ON notifications_delivery
FOR EACH ROW EXECUTE FUNCTION deelvo_delivery_guard();
CREATE FUNCTION deelvo_feed_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
   RAISE EXCEPTION 'Feed revocation history is retained' USING ERRCODE='23514';
 END IF;
 IF TG_OP='UPDATE' AND
    ((NEW.id,NEW.owner_id,NEW.scope,NEW.scope_id,NEW.created_at,NEW.expires_at)
     IS DISTINCT FROM (OLD.id,OLD.owner_id,OLD.scope,OLD.scope_id,OLD.created_at,OLD.expires_at)
     OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at))
 THEN RAISE EXCEPTION 'Feed scope and revocation are permanent' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER feed_guard BEFORE UPDATE OR DELETE ON notifications_calendarfeed
FOR EACH ROW EXECUTE FUNCTION deelvo_feed_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [migrations.RunSQL(SQL)]
