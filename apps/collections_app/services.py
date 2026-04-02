from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from apps.publications.previews import ensure_publication_previews

from .models import Collection, CollectionPublication


def attach_collection_preview_publications(collections: Iterable[Collection], limit: int = 3) -> list[Collection]:
    collection_list = list(collections)
    if not collection_list:
        return collection_list

    collection_map = {collection.pk: collection for collection in collection_list}
    relations = (
        CollectionPublication.objects.filter(collection_id__in=collection_map.keys())
        .select_related(
            "publication",
            "publication__publication_subtype",
            "publication__publication_subtype__publication_type",
            "publication__language",
        )
        .prefetch_related("publication__authors")
        .order_by("collection_id", "-added_at", "publication__title")
    )

    preview_map: dict[int, list] = defaultdict(list)
    preview_publications = []
    for relation in relations:
        bucket = preview_map[relation.collection_id]
        if len(bucket) >= limit:
            continue
        bucket.append(relation.publication)
        preview_publications.append(relation.publication)

    ensure_publication_previews(preview_publications)

    for collection in collection_list:
        collection.preview_publications = preview_map.get(collection.pk, [])

    return collection_list
