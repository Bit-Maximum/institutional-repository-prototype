from __future__ import annotations

import time
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ingestion.services import (
    compute_publication_index_signature,
    rebuild_publication_chunks,
)
from apps.publications.models import Publication
from apps.vector_store.exceptions import VectorStoreDependencyError
from apps.vector_store.services import VectorStoreService


class Command(BaseCommand):
    help = "Reindex publications in Milvus with batching, chunk reuse and incremental skip logic."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Игнорировать сигнатуры и пересобрать чанки заново.")
        parser.add_argument(
            "--recreate-collection",
            action="store_true",
            help="Пересоздать коллекцию Milvus перед индексацией. Ускоряет первичную массовую загрузку.",
        )
        parser.add_argument(
            "--batch-publications",
            type=int,
            default=int(getattr(settings, "VECTOR_REINDEX_PUBLICATION_BATCH_SIZE", 24)),
            help="Сколько изданий накапливать перед пакетной записью в Milvus.",
        )
        parser.add_argument(
            "--skip-vector",
            action="store_true",
            help="Пересчитать извлечение и чанки, но не обновлять Milvus.",
        )
        parser.add_argument(
            "--batch-chunks",
            type=int,
            default=int(getattr(settings, "VECTOR_REINDEX_CHUNK_BATCH_SIZE", 1024)),
            help="Сколько чанков накапливать перед пакетной векторизацией и записью в Milvus.",
        )

    def handle(self, *args, **options):
        force = bool(options["force"])
        recreate_collection = bool(options["recreate_collection"])
        batch_publications = max(1, int(options["batch_publications"]))
        skip_vector = bool(options["skip_vector"])
        batch_chunks = max(1, int(options["batch_chunks"]))

        service = None if skip_vector else VectorStoreService()
        started_at = time.perf_counter()
        parse_seconds = 0.0
        vector_seconds = 0.0
        stats = defaultdict(int)

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
                    "chunks",
                )
                .order_by("pk")
            )

            if service is not None:
                runtime_config = service.get_runtime_config()
                self.stdout.write(
                    "[reindex] Runtime: "
                    f"device={runtime_config['embedding_device']}, fp16={runtime_config['use_fp16']}, "
                    f"embed_batch_size={runtime_config['embed_batch_size']}, "
                    f"embed_text_limit={runtime_config['vector_embed_text_limit']}, "
                    f"upsert_batch_size={runtime_config['upsert_batch_size']}, "
                    f"publication_batch={batch_publications}, chunk_batch={batch_chunks}."
                )
                if recreate_collection:
                    self.stdout.write("[reindex] Recreating Milvus collection...")
                    service.recreate_collection()
                else:
                    service.ensure_collection()
                service.warmup(include_reranker=False)

            pending_vector_chunks: dict[int, list] = {}
            pending_publications: dict[int, Publication] = {}
            pending_chunk_count = 0

            def flush_vector_batch(delete_existing: bool) -> None:
                nonlocal vector_seconds, pending_chunk_count
                if skip_vector or not pending_vector_chunks:
                    return
                vector_started = time.perf_counter()
                upserted = service.replace_publication_chunks_batch(
                    pending_vector_chunks,
                    delete_existing=delete_existing,
                )
                vector_seconds += time.perf_counter() - vector_started
                now = timezone.now()
                for publication in pending_publications.values():
                    publication.vector_indexed_at = now
                Publication.objects.bulk_update(
                    list(pending_publications.values()),
                    ["vector_index_signature", "vector_indexed_at"],
                )
                stats["vector_upserted_chunks"] += int(upserted)
                pending_vector_chunks.clear()
                pending_publications.clear()
                pending_chunk_count = 0

            for publication in queryset.iterator(chunk_size=max(8, batch_publications)):
                signature = compute_publication_index_signature(publication)
                existing_chunks = list(publication.chunks.all())
                for chunk in existing_chunks:
                    chunk.publication = publication

                signature_matches = publication.vector_index_signature == signature
                has_existing_chunks = bool(existing_chunks)

                if not force and signature_matches and has_existing_chunks:
                    if recreate_collection and not skip_vector:
                        pending_vector_chunks[publication.pk] = existing_chunks
                        pending_publications[publication.pk] = publication
                        pending_chunk_count += len(existing_chunks)
                        stats["reused_chunks"] += len(existing_chunks)
                        stats["reused_publications"] += 1
                    else:
                        stats["skipped_publications"] += 1
                    if len(pending_vector_chunks) >= batch_publications or pending_chunk_count >= batch_chunks:
                        flush_vector_batch(delete_existing=not recreate_collection)
                    continue

                parse_started = time.perf_counter()
                _, chunk_objects = rebuild_publication_chunks(publication)
                parse_seconds += time.perf_counter() - parse_started
                publication.vector_index_signature = signature
                stats["rebuilt_publications"] += 1
                stats["rebuilt_chunks"] += len(chunk_objects)

                if skip_vector:
                    publication.vector_indexed_at = timezone.now()
                    publication.save(update_fields=["vector_index_signature", "vector_indexed_at"])
                    continue

                pending_vector_chunks[publication.pk] = chunk_objects
                pending_publications[publication.pk] = publication
                pending_chunk_count += len(chunk_objects)
                if len(pending_vector_chunks) >= batch_publications or pending_chunk_count >= batch_chunks:
                    flush_vector_batch(delete_existing=not recreate_collection)

            flush_vector_batch(delete_existing=not recreate_collection)
        except VectorStoreDependencyError as exc:
            raise CommandError(str(exc)) from exc

        total_seconds = time.perf_counter() - started_at
        processed = stats["rebuilt_publications"] + stats["reused_publications"] + stats["skipped_publications"]
        rate = processed / total_seconds if total_seconds > 0 else 0.0
        summary = (
            "Reindex completed. "
            f"processed={processed}, rebuilt={stats['rebuilt_publications']}, reused={stats['reused_publications']}, "
            f"skipped={stats['skipped_publications']}, rebuilt_chunks={stats['rebuilt_chunks']}, "
            f"vector_upserted_chunks={stats['vector_upserted_chunks']}, parse_s={parse_seconds:.2f}, "
            f"vector_s={vector_seconds:.2f}, total_s={total_seconds:.2f}, docs_per_s={rate:.2f}."
        )
        self.stdout.write(self.style.SUCCESS(summary))
