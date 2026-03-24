from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.services import ingest_publication
from apps.publications.models import Publication
from apps.vector_store.exceptions import VectorStoreDependencyError


class Command(BaseCommand):
    help = "Reindex all publications in Milvus."

    def handle(self, *args, **options):
        try:
            for publication in Publication.objects.filter(is_draft=False).prefetch_related(
                "authors",
                "keywords",
                "scientific_supervisors",
                "publication_subtype",
                "publication_subtype__publication_type",
            ):
                ingest_publication(publication, index_in_vector_store=True)
        except VectorStoreDependencyError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Publications reindexed."))
