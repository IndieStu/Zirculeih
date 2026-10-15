from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("accounts", "AuthorizationRevision").objects.create(pk=1)
    group = apps.get_model("accounts", "Group").objects.create(
        name="Basiszugang", is_baseline=True, description="Sicherer Zugang für neue Konten."
    )
    apps.get_model("accounts", "Grant").objects.create(
        group=group, action="catalog.view_public", effect="allow", scope_kind="organization"
    )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
