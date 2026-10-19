import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from operations import backup


class Command(BaseCommand):
    help = "Offline authenticated DB/media bundle. Never stops writers or executes restored SQL."
    requires_system_checks: list[str] = []

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["key", "pack", "unpack"])
        parser.add_argument("--key-file", type=Path, required=True)
        parser.add_argument("--dump", type=Path)
        parser.add_argument("--media", type=Path)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--bundle", type=Path)
        parser.add_argument("--destination", type=Path)
        parser.add_argument("--build", default="unrecorded")
        parser.add_argument("--maintenance-confirmed", action="store_true")

    def handle(self, *args, **options):
        try:
            action = options["action"]
            if action == "key":
                backup.create_key(options["key_file"])
                result = {"key_created": True}
            elif action == "pack":
                if not all(options[k] is not None for k in ["dump", "media", "output"]):
                    raise backup.BackupError("Dump/media/new output required.")
                result = backup.pack(
                    options["dump"],
                    options["media"],
                    options["output"],
                    options["key_file"],
                    build=options["build"],
                    maintenance_confirmed=options["maintenance_confirmed"],
                )
            else:
                if not all(options[k] is not None for k in ["bundle", "destination"]):
                    raise backup.BackupError("Bundle and new destination required.")
                result = backup.unpack(
                    options["bundle"], options["destination"], options["key_file"]
                )
        except backup.BackupError as exc:
            raise CommandError(str(exc)) from exc
        except OSError as exc:
            raise CommandError("Filesystem operation failed; no overwrite requested.") from exc
        self.stdout.write(json.dumps(result))
