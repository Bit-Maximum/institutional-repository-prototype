from __future__ import annotations

from pathlib import Path

from docx import Document
from pypdf import PdfReader

from apps.publications.models import Publication
from apps.vector_store.services import VectorStoreService


def extract_text_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    return ""


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def extract_text_from_docx(path: Path) -> str:
    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()


def build_search_document(publication: Publication) -> str:
    keyword_text = ", ".join(publication.keywords or [])
    authors = ", ".join(author.full_name for author in publication.authors.all())
    parts = [
        publication.title,
        authors,
        publication.abstract,
        keyword_text,
        publication.extracted_text,
    ]
    return "\n\n".join(part for part in parts if part).strip()


def ingest_publication(publication: Publication, index_in_vector_store: bool = True) -> Publication:
    if publication.file:
        publication.extracted_text = extract_text_from_file(publication.file.path)
    publication.search_document = build_search_document(publication)
    publication.vector_state = Publication.VectorState.PENDING
    publication.save(update_fields=["extracted_text", "search_document", "vector_state", "updated_at"])

    if index_in_vector_store and publication.search_document:
        service = VectorStoreService()
        service.upsert_publication(publication)
    return publication
