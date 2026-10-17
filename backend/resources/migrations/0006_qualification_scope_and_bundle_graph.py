from django.db import migrations

SQL = r"""
CREATE FUNCTION deelvo_qualification_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF (NEW.resource_id,NEW.category_id) IS DISTINCT FROM (OLD.resource_id,OLD.category_id)
 THEN RAISE EXCEPTION 'Qualification scope is immutable' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER qualification_scope_immutable BEFORE UPDATE ON resources_qualificationtype
FOR EACH ROW EXECUTE FUNCTION deelvo_qualification_scope_guard();
CREATE FUNCTION deelvo_bundle_graph_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM accounts_authorizationrevision WHERE id=1 FOR UPDATE;
 IF EXISTS(WITH RECURSIVE reachable(id,path) AS (
   SELECT NEW.component_id,ARRAY[NEW.resource_id,NEW.component_id]
   UNION ALL SELECT c.component_id, r.path||c.component_id
   FROM reachable r JOIN resources_bundlecomponent c ON c.resource_id=r.id
   WHERE NOT c.component_id=ANY(r.path) OR c.component_id=NEW.resource_id
 ) SELECT 1 FROM reachable WHERE id=NEW.resource_id)
 THEN RAISE EXCEPTION 'Cyclic bundle' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER bundle_graph_guard BEFORE INSERT OR UPDATE ON resources_bundlecomponent
FOR EACH ROW EXECUTE FUNCTION deelvo_bundle_graph_guard();
"""


class Migration(migrations.Migration):
    dependencies = [("resources", "0005_bundlecomponent_categoryqualification_and_more")]
    operations = [
        migrations.RunSQL(
            SQL,
            """
      DROP TRIGGER bundle_graph_guard ON resources_bundlecomponent;
      DROP FUNCTION deelvo_bundle_graph_guard();
      DROP TRIGGER qualification_scope_immutable ON resources_qualificationtype;
      DROP FUNCTION deelvo_qualification_scope_guard();
    """,
        )
    ]
