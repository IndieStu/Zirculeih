from django.db import migrations

SQL = r"""
CREATE OR REPLACE FUNCTION deelvo_identifier_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE policy text; expected text;
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Identifiers are retired, never deleted' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' THEN
    IF (NEW.asset_id,NEW.unit_id,NEW.namespace_id,NEW.canonical_value,NEW.kind,NEW.raw_value)
      IS DISTINCT FROM (OLD.asset_id,OLD.unit_id,OLD.namespace_id,
                        OLD.canonical_value,OLD.kind,OLD.raw_value)
      OR (NOT OLD.is_active AND NEW.is_active) THEN
      RAISE EXCEPTION 'Identifier identity is immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  SELECT normalization INTO policy FROM inventory_identifiernamespace WHERE id=NEW.namespace_id;
  expected := btrim(NEW.raw_value, E' \t\r\n');
  IF policy='upper-ascii-v1' THEN expected := translate(expected,
    'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ');
  ELSIF policy<>'exact-v1' THEN
    RAISE EXCEPTION 'Invalid normalization' USING ERRCODE='23514';
  END IF;
  IF NEW.canonical_value<>expected OR expected !~ '^[A-Za-z0-9][A-Za-z0-9._:/ -]{0,127}$' THEN
    RAISE EXCEPTION 'Identifier normalization mismatch' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;

CREATE FUNCTION deelvo_unit_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Units are deactivated, never deleted' USING ERRCODE='23514';
  END IF;
  IF (NEW.resource_id,NEW.asset_id) IS DISTINCT FROM (OLD.resource_id,OLD.asset_id) THEN
    RAISE EXCEPTION 'Unit identity is permanent' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER unit_identity BEFORE UPDATE OR DELETE ON resources_resourceunit
FOR EACH ROW EXECUTE FUNCTION deelvo_unit_guard();
CREATE FUNCTION deelvo_pool_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p_resource uuid; u_resource uuid;
BEGIN
  PERFORM pg_advisory_xact_lock(72403522);
  IF TG_TABLE_NAME='resources_resourcepool' THEN
    IF NEW.resource_id IS DISTINCT FROM OLD.resource_id THEN
      RAISE EXCEPTION 'Pool resource is permanent' USING ERRCODE='23514';
    END IF;
  ELSE
    SELECT resource_id INTO p_resource FROM resources_resourcepool WHERE id=NEW.pool_id;
    SELECT resource_id INTO u_resource FROM resources_resourceunit WHERE id=NEW.unit_id;
    IF p_resource IS DISTINCT FROM u_resource THEN
      RAISE EXCEPTION 'Pool and unit must belong to the same resource' USING ERRCODE='23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER pool_resource BEFORE UPDATE ON resources_resourcepool
FOR EACH ROW EXECUTE FUNCTION deelvo_pool_guard();
CREATE TRIGGER pool_membership_resource BEFORE INSERT OR UPDATE ON resources_poolmembership
FOR EACH ROW EXECUTE FUNCTION deelvo_pool_guard();
CREATE FUNCTION deelvo_resource_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.slug IS DISTINCT FROM OLD.slug OR
     (OLD.archived_at IS NOT NULL AND NEW.archived_at IS NULL) THEN
    RAISE EXCEPTION 'Resource identity and archive are permanent' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER resource_identity BEFORE UPDATE ON resources_resource
FOR EACH ROW EXECUTE FUNCTION deelvo_resource_guard();
"""

REVERSE = r"""

DROP TRIGGER resource_identity ON resources_resource;
DROP FUNCTION deelvo_resource_guard();
DROP TRIGGER pool_membership_resource ON resources_poolmembership;
DROP TRIGGER pool_resource ON resources_resourcepool;
DROP FUNCTION deelvo_pool_guard();
DROP TRIGGER unit_identity ON resources_resourceunit;
DROP FUNCTION deelvo_unit_guard();
CREATE OR REPLACE FUNCTION deelvo_identifier_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE policy text; expected text;
BEGIN
  IF TG_OP='DELETE' THEN
    RAISE EXCEPTION 'Identifiers are retired, never deleted' USING ERRCODE='23514';
  END IF;
  IF TG_OP='UPDATE' THEN
    IF (NEW.asset_id,NEW.namespace_id,NEW.canonical_value,NEW.kind,NEW.raw_value)
      IS DISTINCT FROM (OLD.asset_id,OLD.namespace_id,OLD.canonical_value,OLD.kind,OLD.raw_value)
      OR (NOT OLD.is_active AND NEW.is_active) THEN
      RAISE EXCEPTION 'Identifier identity is immutable' USING ERRCODE='23514';
    END IF;
  END IF;
  SELECT normalization INTO policy FROM inventory_identifiernamespace WHERE id=NEW.namespace_id;
  expected := btrim(NEW.raw_value, E' \t\r\n');
  IF policy='upper-ascii-v1' THEN expected := translate(expected,
    'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ');
  ELSIF policy<>'exact-v1' THEN
    RAISE EXCEPTION 'Invalid normalization' USING ERRCODE='23514';
  END IF;
  IF NEW.canonical_value<>expected OR expected !~ '^[A-Za-z0-9][A-Za-z0-9._:/ -]{0,127}$' THEN
    RAISE EXCEPTION 'Identifier normalization mismatch' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("resources", "0001_initial"),
        ("inventory", "0005_identifier_unit_alter_identifier_asset_and_more"),
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
