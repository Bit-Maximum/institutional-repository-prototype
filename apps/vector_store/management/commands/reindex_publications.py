from django.core.management.base import BaseCommand

from apps.publications.models import Publication
from apps.vector_store.services import VectorStoreService


class Command(BaseCommand):
    help = "Reindex all publications in Milvus."

    def handle(self, *args, **options):
        service = VectorStoreService()
        for publication in Publication.objects.exclude(search_document=""):
            service.upsert_publication(publication)
        self.stdout.write(self.style.SUCCESS("Publications reindexed."))
