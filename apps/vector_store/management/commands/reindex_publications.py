from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.services import ingest_publication
from apps.publications.models import Publication
from apps.vector_store.exceptions import VectorStoreDependencyError


class Command(BaseCommand):
    help = "Reindex all publications in Milvus."

    def handle(self, *args, **options):
        try:
            queryset = (
                Publication.objects.filter(is_draft=False)
                .select_related("publication_subtype", "publication_subtype__publication_type", "language")
                .prefetch_related(
                    "authors",
                    "keywords",
                    "scientific_supervisors",
                    "publishers",
                    "publication_places",
                )
            )
            for publication in queryset:
                ingest_publication(publication, index_in_vector_store=True)
        except VectorStoreDependencyError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Publications reindexed."))
