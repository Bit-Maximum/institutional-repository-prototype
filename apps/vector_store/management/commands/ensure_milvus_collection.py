from django.core.management.base import BaseCommand

from apps.vector_store.services import VectorStoreService


class Command(BaseCommand):
    help = "Create Milvus collection for publications if it does not exist."

    def handle(self, *args, **options):
        VectorStoreService().ensure_collection()
        self.stdout.write(self.style.SUCCESS("Milvus collection is ready."))
