from django.db import migrations

SQL = """
CREATE FUNCTION deelvo_registry_lock() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(72403520);
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER a_registry_lock BEFORE INSERT OR UPDATE OR DELETE ON inventory_identifier
FOR EACH ROW EXECUTE FUNCTION deelvo_registry_lock();
CREATE TRIGGER a_registry_lock BEFORE UPDATE ON inventory_identifiernamespace
FOR EACH ROW EXECUTE FUNCTION deelvo_registry_lock();

CREATE FUNCTION deelvo_custom_value_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE kind text; choices jsonb;
BEGIN
  PERFORM pg_advisory_xact_lock(72403521);
  SELECT d.kind,d.options INTO kind,choices
    FROM inventory_customfielddefinition d WHERE id=NEW.definition_id;
  IF (kind='number' AND NEW.value_number IS NULL)
    OR (kind='date' AND NEW.value_date IS NULL)
    OR (kind='boolean' AND NEW.value_boolean IS NULL)
    OR (kind IN ('text','enum','url') AND NEW.value_text IS NULL)
    OR kind NOT IN ('number','date','boolean','text','enum','url') THEN
    RAISE EXCEPTION 'Custom field value does not match definition' USING ERRCODE='23514';
  END IF;
  IF kind='enum' AND NOT choices ? NEW.value_text THEN
    RAISE EXCEPTION 'Custom enum value not allowed' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER typed_custom_value BEFORE INSERT OR UPDATE ON inventory_customfieldvalue
FOR EACH ROW EXECUTE FUNCTION deelvo_custom_value_guard();

CREATE FUNCTION deelvo_custom_definition_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(72403521);
  IF EXISTS(SELECT 1 FROM inventory_customfieldvalue WHERE definition_id=OLD.id) AND (
    (NEW.key,NEW.kind,NEW.options) IS DISTINCT FROM (OLD.key,OLD.kind,OLD.options)
    OR (OLD.is_sensitive AND NOT NEW.is_sensitive)) THEN
    RAISE EXCEPTION 'Used custom field schema cannot be reinterpreted' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER used_definition_immutable BEFORE UPDATE ON inventory_customfielddefinition
FOR EACH ROW EXECUTE FUNCTION deelvo_custom_definition_guard();
"""
REVERSE = """
DROP TRIGGER used_definition_immutable ON inventory_customfielddefinition;
DROP FUNCTION deelvo_custom_definition_guard();
DROP TRIGGER typed_custom_value ON inventory_customfieldvalue;
DROP FUNCTION deelvo_custom_value_guard();
DROP TRIGGER a_registry_lock ON inventory_identifiernamespace;
DROP TRIGGER a_registry_lock ON inventory_identifier;
DROP FUNCTION deelvo_registry_lock();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_assetmedia_is_sensitive_alter_asset_inventory_number_and_more")
    ]
    operations = [migrations.RunSQL(SQL, REVERSE)]
