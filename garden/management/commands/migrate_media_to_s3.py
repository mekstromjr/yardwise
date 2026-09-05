"""One-shot: copy files from the legacy media PVC into the configured S3
storage (#28). Idempotent - skips keys that already exist with matching size.
Run inside the pod while it still mounts the volume:

    python manage.py migrate_media_to_s3 /data/media
"""

from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copy a local media tree into the active default storage"

    def add_arguments(self, parser):
        parser.add_argument("source", help="Local media root to copy from")

    def handle(self, *args, **options):
        root = Path(options["source"])
        if not root.is_dir():
            raise CommandError(f"{root} is not a directory")
        copied = skipped = 0
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            key = str(f.relative_to(root))
            if default_storage.exists(key) and default_storage.size(key) == f.stat().st_size:
                skipped += 1
                continue
            with f.open("rb") as fh:
                default_storage.save(key, File(fh))
            copied += 1
            self.stdout.write(f"  {key}")
        summary = f"copied {copied}, skipped {skipped} (already present)"
        self.stdout.write(self.style.SUCCESS(summary))
