from __future__ import annotations

import logging
import warnings
from collections import OrderedDict
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

    def __init__(self):
        self.uri = settings.MILVUS_URI
        self.collection_name = settings.MILVUS_COLLECTION
        self._prepare_local_storage_if_needed()
        self.client = MilvusClient(uri=self.uri)
        self.dense_dim = int(getattr(settings, "MILVUS_DENSE_DIM", 1024))
        self.chunk_text_max_length = int(getattr(settings, "MILVUS_CHUNK_TEXT_MAX_LENGTH", 8192))

    def _prepare_local_storage_if_needed(self) -> None:
        parsed = urlparse(self.uri)
        if parsed.scheme in {"http", "https", "tcp", "grpc"}:
            return
        Path(self.uri).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def _get_embedding(self):
        model_name = getattr(settings, "MILVUS_BGE_M3_MODEL", "BAAI/bge-m3")
        if self.__class__._embedding_cache is not None and self.__class__._embedding_model_name == model_name:
            return self.__class__._embedding_cache
        try:
            embedding = model.hybrid.BGEM3EmbeddingFunction(
                model_name=model_name,
                device="cpu",
                use_fp16=False,
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
        if self.client.has_collection(self.collection_name):
            self.client.load_collection(self.collection_name)
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

    def replace_publication_chunks(self, publication: Publication, chunks: list[PublicationChunk]) -> None:
        self.ensure_collection()
        self.delete_publication_chunks(publication.pk)
        if publication.is_draft or not chunks:
            return

        texts = [chunk.vector_document for chunk in chunks if chunk.vector_document]
        if not texts:
            return

        embeddings = self._encode_documents(texts)
        dense_vectors = embeddings["dense"]
        sparse_vectors = embeddings["sparse"]
        payload = []
        text_index = 0
        for chunk in chunks:
            document = chunk.vector_document
            if not document:
                continue
            payload.append(
                {
                    "pk": int(chunk.pk),
                    "publication_id": int(publication.pk),
                    "chunk_index": int(chunk.chunk_index),
                    "title": publication.title[:1024],
                    "chunk_text": chunk.text[: self.chunk_text_max_length],
                    "dense_vector": dense_vectors[text_index],
                    "sparse_vector": self._csr_row_to_dict(sparse_vectors[text_index]),
                }
            )
            text_index += 1

        if payload:
            self.client.upsert(collection_name=self.collection_name, data=payload)

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
            data=[encoded_query["dense"][0]],
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
