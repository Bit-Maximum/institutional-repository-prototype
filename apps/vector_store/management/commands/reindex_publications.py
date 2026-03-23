from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.services import build_search_document, extract_text_from_publication_file
from apps.publications.models import Publication
from apps.vector_store.exceptions import VectorStoreDependencyError
from apps.vector_store.services import VectorStoreService


class Command(BaseCommand):
    help = "Reindex all publications in Milvus."

    def handle(self, *args, **options):
        service = VectorStoreService()
        try:
            for publication in Publication.objects.filter(is_draft=False):
                extracted_text = extract_text_from_publication_file(publication)
                if publication.file and not extracted_text:
                    self.stdout.write(self.style.WARNING(f"Skipping file text extraction for publication #{publication.pk}: {publication.title}"))
                document = build_search_document(publication, extracted_text=extracted_text)
                if document:
                    service.upsert_publication(publication, search_document=document)
        except VectorStoreDependencyError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Publications reindexed."))
