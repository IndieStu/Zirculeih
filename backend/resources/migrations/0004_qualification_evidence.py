from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("resources", "0003_qualificationtype_resource_catalog_area_and_more")]
    operations = [
        migrations.RunSQL(
            """CREATE FUNCTION deelvo_qualification_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Immutable evidence' USING ERRCODE='23514'; END $$;
        CREATE TRIGGER qualification_immutable BEFORE UPDATE OR DELETE
        ON resources_userqualification
        FOR EACH ROW EXECUTE FUNCTION deelvo_qualification_immutable();""",
            "DROP TRIGGER qualification_immutable ON resources_userqualification; "
            "DROP FUNCTION deelvo_qualification_immutable();",
        )
    ]
