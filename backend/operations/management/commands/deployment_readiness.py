import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor

from operations.checks import configuration_problems


class Command(BaseCommand):
    help = (
        "Safe configuration/schema/runtime-role checks; does not contact SMTP/OIDC or change data."
    )
    requires_system_checks: list[str] = []

    def handle(self, *args, **options):
        errors = ["deelvo." + code for code, _ in configuration_problems(settings)]
        role_safe = False
        schema_current = False
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
                flags = cursor.fetchone()
                role_safe = bool(flags) and not any(flags)
                cursor.execute(
                    "SELECT has_schema_privilege(current_user, 'public', 'CREATE'), "
                    "EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND c.relowner=(SELECT oid FROM pg_roles "
                    "WHERE rolname=current_user))"
                )
                ddl_flags = cursor.fetchone()
                role_safe = role_safe and not any(ddl_flags)
                cursor.execute("SHOW server_version_num")
                version = int(cursor.fetchone()[0])
            executor = MigrationExecutor(connection)
            schema_current = not executor.migration_plan(executor.loader.graph.leaf_nodes())
            if not schema_current:
                errors.append("schema_pending")
            if settings.DEPLOYMENT_PROFILE == "production" and (not role_safe or version < 170000):
                errors.append("runtime_role_or_postgres_version")
        except DatabaseError:
            errors.append("database_unavailable")
        self.stdout.write(
            json.dumps(
                dict(
                    profile=settings.DEPLOYMENT_PROFILE,
                    restore_mode=settings.RESTORE_MODE,
                    schema_current=schema_current,
                    runtime_role_safe=role_safe,
                    errors=errors,
                    external_integrations_verified=False,
                )
            )
        )
        if errors:
            raise CommandError("Deployment readiness checks failed; see non-secret codes.")
