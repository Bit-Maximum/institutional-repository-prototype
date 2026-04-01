from django.core.management.base import BaseCommand

from apps.publications.models import Publication
from apps.publications.previews import ensure_publication_preview


class Command(BaseCommand):
    help = "Generate or refresh publication previews for existing records."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate previews even if they already exist.")
        parser.add_argument("--drafts", action="store_true", help="Include drafts in the batch.")

    def handle(self, *args, **options):
        queryset = Publication.objects.all().order_by("pk")
        if not options["drafts"]:
            queryset = queryset.filter(is_draft=False)

        generated = 0
        for publication in queryset.iterator():
            changed = ensure_publication_preview(publication, force=bool(options["force"]))
            if changed:
                generated += 1
                self.stdout.write(self.style.SUCCESS(f"Preview generated for publication #{publication.pk}: {publication.title}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Generated or refreshed previews: {generated}."))
