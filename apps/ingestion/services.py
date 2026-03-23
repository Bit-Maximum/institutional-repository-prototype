from __future__ import annotations

from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation
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


def extract_text_from_publication_file(publication: Publication) -> str:
    if not publication.file:
        return ""
    try:
        file_name = publication.file.name
        if not file_name or not publication.file.storage.exists(file_name):
            return ""
        return extract_text_from_file(publication.file.path)
    except (FileNotFoundError, OSError, SuspiciousFileOperation, ValueError):
        return ""


def build_search_document(publication: Publication, extracted_text: str = "") -> str:
    keyword_text = ", ".join(keyword.name for keyword in publication.keywords.all())
    authors = ", ".join(author.full_name for author in publication.authors.all())
    supervisors = ", ".join(supervisor.full_name for supervisor in publication.scientific_supervisors.all())
    parts = [
        publication.title,
        authors,
        supervisors,
        publication.contents,
        publication.grif_text,
        publication.grant_text,
        keyword_text,
        extracted_text,
    ]
    return "\n\n".join(part for part in parts if part).strip()


def ingest_publication(publication: Publication, index_in_vector_store: bool = True) -> Publication:
    extracted_text = extract_text_from_publication_file(publication)
    if extracted_text:
            merged_contents = publication.contents.strip()
            if merged_contents and extracted_text not in merged_contents:
                publication.contents = f"{merged_contents}\n\n{extracted_text}".strip()
            elif not merged_contents:
                publication.contents = extracted_text
            publication.save(update_fields=["contents"])

    if index_in_vector_store and not publication.is_draft:
        service = VectorStoreService()
        service.upsert_publication(
            publication,
            search_document=build_search_document(publication, extracted_text=extracted_text),
        )
    return publication
