from __future__ import annotations

from pathlib import Path

from django.conf import settings
from pymilvus import DataType, MilvusClient, model

from apps.publications.models import Publication


class VectorStoreService:
    def __init__(self):
        self.uri = settings.MILVUS_URI
        self.collection_name = settings.MILVUS_COLLECTION
        Path(self.uri).parent.mkdir(parents=True, exist_ok=True)
        self.client = MilvusClient(uri=self.uri)
        self.embedding = model.sparse.SpladeEmbeddingFunction(
            model_name=settings.MILVUS_SPLADE_MODEL,
            device="cpu",
        )

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

    def upsert_publication(self, publication: Publication) -> None:
        self.ensure_collection()
        if not publication.search_document:
            return
        embeddings = self.embedding.encode_documents([publication.search_document])
        vector = self._csr_row_to_dict(embeddings[0])
        self.client.upsert(
            collection_name=self.collection_name,
            data={
                "pk": publication.id,
                "title": publication.title[:1024],
                "sparse_vector": vector,
            },
        )
        publication.vector_state = Publication.VectorState.INDEXED
        publication.save(update_fields=["vector_state", "updated_at"])

    def search(self, query: str, limit: int = 20):
        self.ensure_collection()
        query_embedding = self.embedding.encode_queries([query])
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
