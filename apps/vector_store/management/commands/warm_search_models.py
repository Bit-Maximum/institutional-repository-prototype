from django.conf import settings
from django.core.management.base import BaseCommand

from apps.vector_store.services import VectorStoreService


class Command(BaseCommand):
    help = "Предварительно загружает embedding/rerank модели для поиска и коллекцию Milvus."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-reranker",
            action="store_true",
            help="Принудительно прогреть и reranker, даже если он отключён в конфиге.",
        )

    def handle(self, *args, **options):
        service = VectorStoreService()
        service.ensure_collection()
        include_reranker = options["with_reranker"] or bool(getattr(settings, "SEARCH_RERANK_ENABLED", False))
        service.warmup(include_reranker=include_reranker)
        self.stdout.write(self.style.SUCCESS("Поисковые модели и коллекция Milvus прогреты."))
