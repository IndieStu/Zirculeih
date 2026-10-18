# ruff: noqa: E501
from django.db import migrations

SQL = """
ALTER TABLE assetops_inventoryrun ADD CONSTRAINT inventory_run_timestamp_shape CHECK (
 (status='draft' AND started_at IS NULL AND closed_at IS NULL AND report='{}'::jsonb) OR
 (status='active' AND started_at IS NOT NULL AND closed_at IS NULL AND report='{}'::jsonb) OR
 (status IN ('completed','cancelled') AND started_at IS NOT NULL AND closed_at IS NOT NULL
 AND report ? 'cutoff' AND report ? 'assets'));
ALTER TABLE assetops_maintenancetask ADD CONSTRAINT maintenance_timestamp_shape CHECK (
 (status='planned' AND started_at IS NULL AND closed_at IS NULL AND resolution='') OR
 (status='in_progress' AND started_at IS NOT NULL AND closed_at IS NULL AND resolution='') OR
 (status IN ('completed','cancelled') AND closed_at IS NOT NULL AND resolution<>''));
CREATE FUNCTION deelvo_discrepancy_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Discrepancy history is permanent' USING ERRCODE='23514'; END IF;
 IF (NEW.run_id,NEW.asset_id,NEW.kind) IS DISTINCT FROM (OLD.run_id,OLD.asset_id,OLD.kind)
 OR OLD.resolved_at IS NOT NULL THEN RAISE EXCEPTION 'Immutable discrepancy identity/decision' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER discrepancy_guard BEFORE UPDATE OR DELETE ON assetops_discrepancy FOR EACH ROW EXECUTE FUNCTION deelvo_discrepancy_guard();
CREATE FUNCTION deelvo_inventory_run_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Run history is permanent' USING ERRCODE='23514'; END IF;
 IF (NEW.id,NEW.scope,NEW.scope_id,NEW.created_by_id,NEW.created_at,NEW.title)
 IS DISTINCT FROM (OLD.id,OLD.scope,OLD.scope_id,OLD.created_by_id,OLD.created_at,OLD.title)
 OR OLD.status IN ('completed','cancelled') THEN
 RAISE EXCEPTION 'Immutable run history' USING ERRCODE='23514'; END IF;
 IF NOT ((OLD.status='draft' AND NEW.status='active') OR (OLD.status='active' AND NEW.status IN ('completed','cancelled')))
 OR NEW.revision<>OLD.revision+1 THEN
 RAISE EXCEPTION 'Invalid run transition' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER inventory_run_guard BEFORE UPDATE OR DELETE ON assetops_inventoryrun FOR EACH ROW EXECUTE FUNCTION deelvo_inventory_run_guard();
CREATE FUNCTION deelvo_inventory_child_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE state text;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Snapshot and observations are immutable' USING ERRCODE='23514'; END IF;
 SELECT status INTO state FROM assetops_inventoryrun WHERE id=NEW.run_id FOR UPDATE;
 IF (TG_TABLE_NAME='assetops_expectedasset' AND state<>'draft') OR
 (TG_TABLE_NAME='assetops_observation' AND state<>'active') THEN
 RAISE EXCEPTION 'Run closed or snapshot frozen' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER expected_asset_guard BEFORE INSERT OR UPDATE OR DELETE ON assetops_expectedasset FOR EACH ROW EXECUTE FUNCTION deelvo_inventory_child_guard();
CREATE TRIGGER observation_guard BEFORE INSERT OR UPDATE OR DELETE ON assetops_observation FOR EACH ROW EXECUTE FUNCTION deelvo_inventory_child_guard();
CREATE FUNCTION deelvo_maintenance_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Maintenance history is permanent' USING ERRCODE='23514'; END IF;
 IF (NEW.asset_id,NEW.reported_by_id,NEW.created_at) IS DISTINCT FROM (OLD.asset_id,OLD.reported_by_id,OLD.created_at)
 OR OLD.status IN ('completed','cancelled') THEN RAISE EXCEPTION 'Immutable maintenance history' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER maintenance_guard BEFORE UPDATE OR DELETE ON assetops_maintenancetask FOR EACH ROW EXECUTE FUNCTION deelvo_maintenance_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("assetops", "0001_initial")]
    operations = [migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop)]
