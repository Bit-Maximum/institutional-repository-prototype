from __future__ import annotations

import logging
import warnings

import numpy as np
from collections import OrderedDict
from itertools import islice
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from pymilvus import DataType, MilvusClient, model

from apps.publications.models import Publication, PublicationChunk
from apps.vector_store.exceptions import VectorStoreDependencyError

logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
warnings.filterwarnings(
    "ignore",
    message=r"You're using a XLMRobertaTokenizerFast tokenizer.*",
)


class VectorStoreService:
    _embedding_cache = None
    _embedding_model_name: str | None = None
    _reranker_cache = None
    _reranker_model_name: str | None = None
    _query_cache: OrderedDict[tuple[str, str], dict] = OrderedDict()
    _loaded_collection_keys: set[tuple[str, str]] = set()

    def __init__(self):
        self.uri = settings.MILVUS_URI
        self.collection_name = settings.MILVUS_COLLECTION
        self._prepare_local_storage_if_needed()
        self.client = MilvusClient(uri=self.uri)
        self.dense_dim = int(getattr(settings, "MILVUS_DENSE_DIM", 1024))
        self.chunk_text_max_length = int(getattr(settings, "MILVUS_CHUNK_TEXT_MAX_LENGTH", 8192))
        self.embed_batch_size = max(1, int(getattr(settings, "MILVUS_BGE_M3_BATCH_SIZE", 16)))
        self.upsert_batch_size = max(1, int(getattr(settings, "MILVUS_UPSERT_BATCH_SIZE", 128)))
        self.delete_batch_size = max(1, int(getattr(settings, "MILVUS_DELETE_BATCH_SIZE", 64)))
        self.vector_embed_text_limit = max(1, int(getattr(settings, "VECTOR_INDEX_MAX_EMBED_TEXTS", 128)))

    def _resolve_embedding_device(self) -> str:
        device = str(getattr(settings, "MILVUS_BGE_M3_DEVICE", "cpu")).strip() or "cpu"
        if not device.startswith("cuda"):
            return device
        try:
            import torch
        except Exception:
            logging.warning("CUDA device requested for BGE-M3, but torch is unavailable. Falling back to CPU.")
            return "cpu"
        if not torch.cuda.is_available():
            logging.warning("CUDA device requested for BGE-M3, but CUDA is not available in the current torch build. Falling back to CPU.")
            return "cpu"
        return device

    def _normalize_dense_vector(self, vector) -> np.ndarray:
        if isinstance(vector, np.ndarray):
            array = vector
        else:
            array = np.asarray(vector)
        if array.dtype != np.float32:
            array = array.astype(np.float32, copy=False)
        return np.ascontiguousarray(array.reshape(-1), dtype=np.float32)

    def _prepare_local_storage_if_needed(self) -> None:
        parsed = urlparse(self.uri)
        if parsed.scheme in {"http", "https", "tcp", "grpc"}:
            return
        Path(self.uri).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def _collection_cache_key(self) -> tuple[str, str]:
        return (self.uri, self.collection_name)

    def _get_embedding(self):
        model_name = getattr(settings, "MILVUS_BGE_M3_MODEL", "BAAI/bge-m3")
        if self.__class__._embedding_cache is not None and self.__class__._embedding_model_name == model_name:
            return self.__class__._embedding_cache
        try:
            embedding = model.hybrid.BGEM3EmbeddingFunction(
                model_name=model_name,
                batch_size=self.embed_batch_size,
                device=self._resolve_embedding_device(),
                use_fp16=bool(getattr(settings, "MILVUS_BGE_M3_USE_FP16", False)),
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
        except ModuleNotFoundError as exc:
            if exc.name in {"torch", "FlagEmbedding", "hf_xet"}:
                raise VectorStoreDependencyError(
                    "Для семантического поиска нужен стек BGE-M3. "
                    "Выполни uv sync, чтобы в окружение попали torch, FlagEmbedding и hf_xet."
                ) from exc
            raise
        self.__class__._embedding_cache = embedding
        self.__class__._embedding_model_name = model_name
        return embedding

    def _get_reranker(self):
        if not getattr(settings, "SEARCH_RERANK_ENABLED", True):
            return None

        model_name = getattr(settings, "SEARCH_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
        if self.__class__._reranker_cache is not None and self.__class__._reranker_model_name == model_name:
            return self.__class__._reranker_cache
        try:
            reranker = model.reranker.BGERerankFunction(model_name=model_name, device="cpu")
        except (ImportError, ModuleNotFoundError) as exc:
            missing_name = getattr(exc, "name", None)
            if missing_name in {None, "torch", "FlagEmbedding", "hf_xet"}:
                raise VectorStoreDependencyError(
                    "Для этапа rerank нужен стек BGE reranker. "
                    "Выполни uv sync, чтобы в окружение попали torch, FlagEmbedding и hf_xet."
                ) from exc
            raise
        self.__class__._reranker_cache = reranker
        self.__class__._reranker_model_name = model_name
        return reranker

    def warmup(self, include_reranker: bool | None = None) -> None:
        self._get_embedding()
        if include_reranker is None:
            include_reranker = bool(getattr(settings, "SEARCH_RERANK_ENABLED", False))
        if include_reranker:
            self._get_reranker()

    def ensure_collection(self) -> None:
        cache_key = self._collection_cache_key()
        if cache_key in self.__class__._loaded_collection_keys:
            return

        if self.client.has_collection(self.collection_name):
            self.client.load_collection(self.collection_name)
            self.__class__._loaded_collection_keys.add(cache_key)
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_fields=False)
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="publication_id", datatype=DataType.INT64)
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
        schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=1024)
        schema.add_field(field_name="chunk_text", datatype=DataType.VARCHAR, max_length=self.chunk_text_max_length)
        schema.add_field(field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=self.dense_dim)
        schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

        self.client.create_collection(collection_name=self.collection_name, schema=schema)
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_name="dense_auto_index",
            index_type="AUTOINDEX",
            metric_type="IP",
            params={},
        )
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_inverted_index",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            params={"drop_ratio_build": settings.MILVUS_DROP_RATIO_BUILD},
        )
        self.client.create_index(collection_name=self.collection_name, index_params=index_params)
        self.client.load_collection(self.collection_name)
        self.__class__._loaded_collection_keys.add(cache_key)

    def recreate_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
        self.__class__._loaded_collection_keys.discard(self._collection_cache_key())
        self.ensure_collection()

    def _csr_row_to_dict(self, csr_matrix_row) -> dict[int, float]:
        row = csr_matrix_row.tocsr()
        return {int(index): float(value) for index, value in zip(row.indices, row.data, strict=False)}

    def _encode_documents(self, texts: list[str]) -> dict[str, list]:
        return self._get_embedding().encode_documents(texts)

    def _encode_queries(self, texts: list[str]) -> dict[str, list]:
        if len(texts) != 1:
            return self._get_embedding().encode_queries(texts)

        model_name = getattr(settings, "MILVUS_BGE_M3_MODEL", "BAAI/bge-m3")
        key = (model_name, texts[0])
        cache = self.__class__._query_cache
        if key in cache:
            cache.move_to_end(key)
            return cache[key]

        encoded = self._get_embedding().encode_queries(texts)
        cache[key] = encoded
        max_size = max(8, int(getattr(settings, "MILVUS_QUERY_CACHE_SIZE", 64)))
        while len(cache) > max_size:
            cache.popitem(last=False)
        return encoded

    def delete_publication_chunks(self, publication_id: int) -> None:
        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            filter=f"publication_id == {int(publication_id)}",
        )

    def delete_publication_chunks_many(self, publication_ids: list[int]) -> None:
        self.ensure_collection()
        unique_ids = [int(pub_id) for pub_id in sorted(set(publication_ids)) if pub_id is not None]
        if not unique_ids:
            return
        for start in range(0, len(unique_ids), self.delete_batch_size):
            batch_ids = unique_ids[start : start + self.delete_batch_size]
            filter_expr = " or ".join(f"publication_id == {pub_id}" for pub_id in batch_ids)
            self.client.delete(collection_name=self.collection_name, filter=filter_expr)

    def _batched(self, items, batch_size: int):
        iterator = iter(items)
        while True:
            batch = list(islice(iterator, batch_size))
            if not batch:
                break
            yield batch

    def _build_vector_document(self, publication: Publication, chunk: PublicationChunk, header_cache: dict[int, str]) -> str:
        publication_id = int(publication.pk)
        header = header_cache.get(publication_id)
        if header is None:
            metadata_parts = [publication.title]
            authors = ", ".join(author.full_name for author in publication.authors.all())
            if authors:
                metadata_parts.append(f"Авторы: {authors}")
            if publication.publication_type:
                metadata_parts.append(f"Тип: {publication.publication_type.name}")
            if publication.publication_subtype:
                metadata_parts.append(f"Подтип: {publication.publication_subtype.name}")
            if publication.language:
                metadata_parts.append(f"Язык: {publication.language.name}")
            keywords = ", ".join(keyword.name for keyword in publication.keywords.all())
            if keywords:
                metadata_parts.append(f"Ключевые слова: {keywords}")
            if publication.publication_year:
                metadata_parts.append(f"Год: {publication.publication_year}")
            header = "\n".join(part for part in metadata_parts if part)
            header_cache[publication_id] = header
        prefix = "Фрагмент документа" if chunk.source_kind == "fulltext" else "Метаданные документа"
        if header:
            return f"{header}\n\n{prefix}: {chunk.text}".strip()
        return chunk.text.strip()

    def upsert_chunks(self, chunks: list[PublicationChunk]) -> int:
        self.ensure_collection()
        prepared_rows: list[tuple[PublicationChunk, str]] = []
        header_cache: dict[int, str] = {}
        for chunk in chunks:
            publication = getattr(chunk, "publication", None)
            if publication is None:
                publication = chunk.publication
            vector_document = self._build_vector_document(publication, chunk, header_cache)
            if vector_document:
                prepared_rows.append((chunk, vector_document))

        upserted = 0
        for batch in self._batched(prepared_rows, self.vector_embed_text_limit):
            texts = [text for _, text in batch]
            embeddings = self._encode_documents(texts)
            dense_vectors = embeddings["dense"]
            sparse_vectors = embeddings["sparse"]
            payload: list[dict] = []
            for row_index, (chunk, _) in enumerate(batch):
                publication = getattr(chunk, "publication", None) or chunk.publication
                payload.append(
                    {
                        "pk": int(chunk.pk),
                        "publication_id": int(publication.pk),
                        "chunk_index": int(chunk.chunk_index),
                        "title": publication.title[:1024],
                        "chunk_text": chunk.text[: self.chunk_text_max_length],
                        "dense_vector": self._normalize_dense_vector(dense_vectors[row_index]),
                        "sparse_vector": self._csr_row_to_dict(sparse_vectors[row_index]),
                    }
                )
            for upsert_batch in self._batched(payload, self.upsert_batch_size):
                self.client.upsert(collection_name=self.collection_name, data=upsert_batch)
                upserted += len(upsert_batch)
        return upserted

    def replace_publication_chunks(self, publication: Publication, chunks: list[PublicationChunk]) -> None:
        self.ensure_collection()
        self.delete_publication_chunks(publication.pk)
        if publication.is_draft or not chunks:
            return
        self.upsert_chunks(chunks)

    def replace_publication_chunks_batch(self, publication_chunks: dict[int, list[PublicationChunk]], *, delete_existing: bool = True) -> int:
        self.ensure_collection()
        publication_ids = [int(pub_id) for pub_id, chunks in publication_chunks.items() if chunks]
        if delete_existing and publication_ids:
            self.delete_publication_chunks_many(publication_ids)

        all_chunks: list[PublicationChunk] = []
        for pub_id in publication_ids:
            all_chunks.extend(publication_chunks.get(pub_id, []))
        if not all_chunks:
            return 0
        return self.upsert_chunks(all_chunks)

    def _parse_hits(self, result) -> list[dict]:
        hits: list[dict] = []
        for batch in result:
            for item in batch:
                entity = item.get("entity", {}) or {}
                chunk_pk = item.get("id") or item.get("pk") or entity.get("pk")
                publication_id = entity.get("publication_id")
                if chunk_pk is None or publication_id is None:
                    continue
                hits.append(
                    {
                        "chunk_pk": int(chunk_pk),
                        "publication_id": int(publication_id),
                        "chunk_index": int(entity.get("chunk_index") or 0),
                        "score": float(item.get("distance") or 0.0),
                        "title": entity.get("title") or "",
                        "chunk_text": entity.get("chunk_text") or "",
                    }
                )
        return hits

    def _search_dense_with_encoded(self, encoded_query: dict[str, list], limit: int) -> list[dict]:
        result = self.client.search(
            collection_name=self.collection_name,
            data=[self._normalize_dense_vector(encoded_query["dense"][0])],
            anns_field="dense_vector",
            limit=limit,
            output_fields=["publication_id", "chunk_index", "title", "chunk_text"],
            search_params={"metric_type": "IP", "params": {}},
        )
        return self._parse_hits(result)

    def _search_sparse_with_encoded(self, encoded_query: dict[str, list], limit: int) -> list[dict]:
        result = self.client.search(
            collection_name=self.collection_name,
            data=[self._csr_row_to_dict(encoded_query["sparse"][0])],
            anns_field="sparse_vector",
            limit=limit,
            output_fields=["publication_id", "chunk_index", "title", "chunk_text"],
            search_params={
                "metric_type": "IP",
                "params": {"drop_ratio_search": settings.MILVUS_DROP_RATIO_SEARCH},
            },
        )
        return self._parse_hits(result)

    def search_dense_chunks(self, query: str, limit: int = 50) -> list[dict]:
        self.ensure_collection()
        encoded = self._encode_queries([query])
        return self._search_dense_with_encoded(encoded, limit)

    def search_sparse_chunks(self, query: str, limit: int = 50) -> list[dict]:
        self.ensure_collection()
        encoded = self._encode_queries([query])
        return self._search_sparse_with_encoded(encoded, limit)

    def search_hybrid_chunks(self, query: str, limit: int = 50) -> list[dict]:
        self.ensure_collection()
        encoded = self._encode_queries([query])
        dense_hits = self._search_dense_with_encoded(encoded, limit)
        sparse_hits = self._search_sparse_with_encoded(encoded, limit)
        rank_constant = int(getattr(settings, "MILVUS_RRF_K", 60))
        dense_weight = float(getattr(settings, "MILVUS_HYBRID_DENSE_WEIGHT", 0.65))
        sparse_weight = float(getattr(settings, "MILVUS_HYBRID_SPARSE_WEIGHT", 0.35))

        combined: dict[int, dict] = {}
        for rank, hit in enumerate(dense_hits, start=1):
            entry = combined.setdefault(
                hit["chunk_pk"],
                {**hit, "score": 0.0, "dense_score": hit["score"], "sparse_score": 0.0},
            )
            entry["score"] += dense_weight / (rank_constant + rank)
            entry["dense_score"] = max(entry["dense_score"], hit["score"])
        for rank, hit in enumerate(sparse_hits, start=1):
            entry = combined.setdefault(
                hit["chunk_pk"],
                {**hit, "score": 0.0, "dense_score": 0.0, "sparse_score": hit["score"]},
            )
            entry["score"] += sparse_weight / (rank_constant + rank)
            entry["sparse_score"] = max(entry["sparse_score"], hit["score"])
        return sorted(combined.values(), key=lambda item: item["score"], reverse=True)

    def rerank_documents(self, query: str, documents: list[str], top_k: int | None = None) -> list[dict]:
        reranker = self._get_reranker()
        if reranker is None or not documents:
            return []

        limit = max(1, min(len(documents), int(top_k or len(documents))))
        results = reranker(query=query, documents=documents, top_k=limit)
        normalized_results: list[dict] = []
        for item in results:
            index = getattr(item, "index", None)
            score = getattr(item, "score", None)
            text = getattr(item, "text", None)
            if index is None or score is None:
                continue
            normalized_results.append(
                {
                    "index": int(index),
                    "score": float(score),
                    "text": text or documents[int(index)],
                }
            )
        return normalized_results
