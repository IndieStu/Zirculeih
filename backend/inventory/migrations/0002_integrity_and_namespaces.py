from django.db import migrations

SQL = r"""
CREATE FUNCTION deelvo_tree_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cyclic boolean;
BEGIN
  PERFORM pg_advisory_xact_lock(72403519);
  IF NEW.parent_id IS NOT NULL THEN
    EXECUTE format('WITH RECURSIVE ancestors AS (
      SELECT id, parent_id FROM %I WHERE id = $1
      UNION SELECT p.id,p.parent_id FROM %I p JOIN ancestors a ON p.id=a.parent_id
    ) SELECT EXISTS(SELECT 1 FROM ancestors WHERE id=$2)', TG_TABLE_NAME, TG_TABLE_NAME)
    INTO cyclic USING NEW.parent_id, NEW.id;
    IF cyclic THEN RAISE EXCEPTION 'cyclic inventory tree' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER location_acyclic BEFORE INSERT OR UPDATE OF parent_id ON inventory_location
FOR EACH ROW EXECUTE FUNCTION deelvo_tree_guard();
CREATE TRIGGER category_acyclic BEFORE INSERT OR UPDATE OF parent_id ON inventory_category
FOR EACH ROW EXECUTE FUNCTION deelvo_tree_guard();

CREATE FUNCTION deelvo_identifier_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
CREATE TRIGGER identifier_immutable BEFORE INSERT OR UPDATE OR DELETE ON inventory_identifier
FOR EACH ROW EXECUTE FUNCTION deelvo_identifier_guard();

CREATE FUNCTION deelvo_namespace_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF (NEW.key,NEW.normalization) IS DISTINCT FROM (OLD.key,OLD.normalization)
     AND EXISTS (SELECT 1 FROM inventory_identifier WHERE namespace_id=OLD.id) THEN
    RAISE EXCEPTION 'Namespace normalization is versioned and immutable' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER namespace_immutable BEFORE UPDATE ON inventory_identifiernamespace
FOR EACH ROW EXECUTE FUNCTION deelvo_namespace_guard();

CREATE FUNCTION deelvo_asset_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.inventory_number IS DISTINCT FROM OLD.inventory_number THEN
    RAISE EXCEPTION 'Inventory number is permanent' USING ERRCODE='23514';
  END IF;
  IF OLD.archived_at IS NOT NULL AND NEW.archived_at IS NULL THEN
    RAISE EXCEPTION 'Asset archive is permanent in this version' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER asset_permanent_identity BEFORE UPDATE ON inventory_asset
FOR EACH ROW EXECUTE FUNCTION deelvo_asset_guard();
"""
REVERSE = """
DROP TRIGGER asset_permanent_identity ON inventory_asset;
DROP FUNCTION deelvo_asset_guard();
DROP TRIGGER namespace_immutable ON inventory_identifiernamespace;
DROP FUNCTION deelvo_namespace_guard();
DROP TRIGGER identifier_immutable ON inventory_identifier;
DROP FUNCTION deelvo_identifier_guard();
DROP TRIGGER category_acyclic ON inventory_category;
DROP TRIGGER location_acyclic ON inventory_location;
DROP FUNCTION deelvo_tree_guard();
"""


def seed(apps, schema_editor):
    ns = apps.get_model("inventory", "IdentifierNamespace")
    ns.objects.create(key="deelvo", name="Deelvo-Codes", normalization="exact-v1")
    ns.objects.create(key="inventory", name="Inventarnummern", normalization="exact-v1")


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial")]
    operations = [
        migrations.RunSQL(SQL, REVERSE),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
