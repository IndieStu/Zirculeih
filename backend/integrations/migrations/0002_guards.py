from django.db import migrations

SQL = """
CREATE FUNCTION deelvo_api_client_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'integration history is immutable' USING ERRCODE='23514';
  END IF;
  IF TG_OP = 'UPDATE' AND (
    (to_jsonb(NEW) - 'retired_at') IS DISTINCT FROM (to_jsonb(OLD) - 'retired_at')
    OR (OLD.retired_at IS NOT NULL AND NEW.retired_at IS DISTINCT FROM OLD.retired_at)
  ) THEN
    RAISE EXCEPTION 'integration ceiling is immutable' USING ERRCODE='23514';
  END IF;
  IF jsonb_typeof(NEW.capabilities) <> 'array'
    OR jsonb_array_length(NEW.capabilities) NOT BETWEEN 1 AND 20
  THEN
    RAISE EXCEPTION 'invalid capabilities' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER deelvo_api_client_guard BEFORE INSERT OR UPDATE OR DELETE
ON integrations_integrationclient
FOR EACH ROW EXECUTE FUNCTION deelvo_api_client_guard();
CREATE FUNCTION deelvo_api_token_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'token history is immutable' USING ERRCODE='23514';
  END IF;
  IF TG_OP = 'UPDATE' AND (
    (to_jsonb(NEW) - 'revoked_at') IS DISTINCT FROM (to_jsonb(OLD) - 'revoked_at')
    OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at)
  ) THEN
    RAISE EXCEPTION 'token ceiling is immutable' USING ERRCODE='23514';
  END IF;
  IF jsonb_typeof(NEW.capabilities) <> 'array'
    OR jsonb_array_length(NEW.capabilities) NOT BETWEEN 1 AND 20
    OR NEW.digest !~ '^[0-9a-f]{64}$' OR NEW.expires_at > NEW.created_at + interval '90 days'
  THEN
    RAISE EXCEPTION 'invalid token ceiling' USING ERRCODE='23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER deelvo_api_token_guard BEFORE INSERT OR UPDATE OR DELETE
ON integrations_integrationtoken
FOR EACH ROW EXECUTE FUNCTION deelvo_api_token_guard();
CREATE FUNCTION deelvo_api_import_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'import ownership is immutable' USING ERRCODE='23514';
END $$;
CREATE TRIGGER deelvo_api_import_guard BEFORE UPDATE OR DELETE
ON integrations_apiimport
FOR EACH ROW EXECUTE FUNCTION deelvo_api_import_guard();
"""
REVERSE = """
DROP TRIGGER deelvo_api_import_guard
ON integrations_apiimport;
DROP FUNCTION deelvo_api_import_guard();
DROP TRIGGER deelvo_api_token_guard
ON integrations_integrationtoken;
DROP FUNCTION deelvo_api_token_guard();
DROP TRIGGER deelvo_api_client_guard
ON integrations_integrationclient;
DROP FUNCTION deelvo_api_client_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("integrations", "0001_initial")]
    operations = [migrations.RunSQL(SQL, REVERSE)]
