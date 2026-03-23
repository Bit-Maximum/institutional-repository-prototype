from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from pymilvus import DataType, MilvusClient, model

from apps.publications.models import Publication
from apps.vector_store.exceptions import VectorStoreDependencyError


class VectorStoreService:
    def __init__(self):
        self.uri = settings.MILVUS_URI
        self.collection_name = settings.MILVUS_COLLECTION
        self._prepare_local_storage_if_needed()
        self.client = MilvusClient(uri=self.uri)
        self._embedding = None

    def _prepare_local_storage_if_needed(self) -> None:
        parsed = urlparse(self.uri)
        if parsed.scheme in {"http", "https", "tcp", "grpc"}:
            return
        Path(self.uri).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    def _patch_tokenizer_compatibility(self, embedding) -> None:
        candidate_paths = (("model", "tokenizer"), ("tokenizer",))
        for candidate_path in candidate_paths:
            target = embedding
            for attr in candidate_path:
                target = getattr(target, attr, None)
                if target is None:
                    break
            if target is None:
                continue
            if not hasattr(target, "batch_encode_plus") and callable(target):
                target.batch_encode_plus = target.__call__
            if not hasattr(target, "encode_plus") and callable(target):
                target.encode_plus = target.__call__

    def _get_embedding(self):
        if self._embedding is not None:
            return self._embedding
        try:
            self._embedding = model.sparse.SpladeEmbeddingFunction(
                model_name=settings.MILVUS_SPLADE_MODEL,
                device="cpu",
            )
            self._patch_tokenizer_compatibility(self._embedding)
        except ModuleNotFoundError as exc:
            if exc.name == "torch":
                raise VectorStoreDependencyError(
                    "PyTorch не найден в текущем окружении. "
                    "Команда ensure_milvus_collection может работать без него, "
                    "но для семантической индексации и поиска нужно установить torch "
                    "именно в активное окружение проекта."
                ) from exc
            raise
        return self._embedding

    def _handle_embedding_attribute_error(self, exc: AttributeError) -> None:
        if "batch_encode_plus" in str(exc):
            raise VectorStoreDependencyError(
                "Текущая версия transformers несовместима с SPLADE-обёрткой из pymilvus. "
                "Обновлённый проект фиксирует совместимую ветку dependencies, поэтому "
                "после получения этой версии проекта нужно повторно выполнить uv sync."
            ) from exc
        raise exc

    def ensure_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_fields=False)
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="title", datatype=DataType.VARCHAR, max_length=1024)
        schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

        self.client.create_collection(collection_name=self.collection_name, schema=schema)
        index_params = self.client.prepare_index_params()
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

    def upsert_publication(self, publication: Publication, search_document: str | None = None) -> None:
        self.ensure_collection()
        document = (search_document or publication.search_document).strip()
        if not document or publication.is_draft:
            return
        try:
            embeddings = self._get_embedding().encode_documents([document])
        except AttributeError as exc:
            self._handle_embedding_attribute_error(exc)
        vector = self._csr_row_to_dict(embeddings[0])
        self.client.upsert(
            collection_name=self.collection_name,
            data={
                "pk": publication.pk,
                "title": publication.title[:1024],
                "sparse_vector": vector,
            },
        )

    def search(self, query: str, limit: int = 20):
        self.ensure_collection()
        try:
            query_embedding = self._get_embedding().encode_queries([query])
        except AttributeError as exc:
            self._handle_embedding_attribute_error(exc)
        vector = self._csr_row_to_dict(query_embedding[0])
        result = self.client.search(
            collection_name=self.collection_name,
            data=[vector],
            limit=limit,
            output_fields=["title"],
            search_params={
                "metric_type": "IP",
                "params": {"drop_ratio_search": settings.MILVUS_DROP_RATIO_SEARCH},
            },
        )
        hits = []
        for batch in result:
            for item in batch:
                publication_id = item.get("id") or item.get("pk") or item.get("entity", {}).get("pk")
                hits.append(
                    {
                        "publication_id": int(publication_id),
                        "score": float(item["distance"]),
                        "title": item.get("entity", {}).get("title") or "",
                    }
                )
        return hits
