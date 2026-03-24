from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from docx import Document
from pypdf import PdfReader

from apps.publications.models import Publication, PublicationChunk
from apps.vector_store.services import VectorStoreService


@dataclass(slots=True)
class ExtractedSegment:
    text: str
    page_start: int | None = None
    page_end: int | None = None


@dataclass(slots=True)
class ChunkPayload:
    chunk_index: int
    text: str
    chunk_text: str
    page_start: int | None = None
    page_end: int | None = None
    char_count: int = 0
    word_count: int = 0


_WORD_RE = re.compile(r"\S+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str:
    return _WHITESPACE_RE.sub(" ", (value or "").strip())


def extract_text_from_file(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    return ""


def extract_text_from_pdf(path: Path) -> str:
    return "\n".join(segment.text for segment in extract_segments_from_pdf(path) if segment.text).strip()


def extract_text_from_docx(path: Path) -> str:
    return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs if paragraph.text).strip()


def extract_segments_from_file(file_path: str | Path) -> list[ExtractedSegment]:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_segments_from_pdf(path)
    if suffix == ".docx":
        return extract_segments_from_docx(path)
    return []


def extract_segments_from_pdf(path: Path) -> list[ExtractedSegment]:
    reader = PdfReader(str(path))
    segments: list[ExtractedSegment] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        if text:
            segments.append(ExtractedSegment(text=text, page_start=page_number, page_end=page_number))
    return segments


def extract_segments_from_docx(path: Path) -> list[ExtractedSegment]:
    paragraphs = [normalize_text(paragraph.text) for paragraph in Document(str(path)).paragraphs]
    text = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    if not text:
        return []
    return [ExtractedSegment(text=text)]


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


def _split_text_into_windows(text: str, max_words: int, overlap_words: int, max_chars: int) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    units = [normalize_text(unit) for unit in _SENTENCE_SPLIT_RE.split(normalized) if normalize_text(unit)]
    if not units:
        units = [normalized]

    chunks: list[str] = []
    current_units: list[str] = []
    current_word_count = 0
    current_char_count = 0

    def flush() -> None:
        nonlocal current_units, current_word_count, current_char_count
        if not current_units:
            return
        chunk_text = normalize_text(" ".join(current_units))
        if chunk_text:
            chunks.append(chunk_text)
        overlap_seed: list[str] = []
        if overlap_words > 0 and current_units:
            words_remaining = overlap_words
            for unit in reversed(current_units):
                overlap_seed.insert(0, unit)
                words_remaining -= len(_WORD_RE.findall(unit))
                if words_remaining <= 0:
                    break
        current_units = overlap_seed
        current_word_count = sum(len(_WORD_RE.findall(unit)) for unit in current_units)
        current_char_count = sum(len(unit) for unit in current_units) + max(0, len(current_units) - 1)

    for unit in units:
        unit_words = len(_WORD_RE.findall(unit))
        unit_chars = len(unit)
        projected_words = current_word_count + unit_words
        projected_chars = current_char_count + unit_chars + (1 if current_units else 0)
        if current_units and (projected_words > max_words or projected_chars > max_chars):
            flush()
        if unit_words > max_words or unit_chars > max_chars:
            words = unit.split()
            step = max(1, max_words - overlap_words)
            for start in range(0, len(words), step):
                piece_words = words[start : start + max_words]
                piece_text = normalize_text(" ".join(piece_words))
                if piece_text:
                    chunks.append(piece_text[:max_chars].strip())
            current_units = []
            current_word_count = 0
            current_char_count = 0
            continue
        current_units.append(unit)
        current_word_count += unit_words
        current_char_count += unit_chars + (1 if len(current_units) > 1 else 0)

    if current_units:
        flush()

    deduped: list[str] = []
    previous = None
    for chunk in chunks:
        if chunk and chunk != previous:
            deduped.append(chunk)
            previous = chunk
    return deduped


def chunk_segments(segments: list[ExtractedSegment], max_words: int, overlap_words: int, max_chars: int) -> list[ChunkPayload]:
    chunk_payloads: list[ChunkPayload] = []
    chunk_index = 0

    for segment in segments:
        windows = _split_text_into_windows(segment.text, max_words=max_words, overlap_words=overlap_words, max_chars=max_chars)
        for window in windows:
            chunk_payloads.append(
                ChunkPayload(
                    chunk_index=chunk_index,
                    text=window,
                    chunk_text=window,
                    page_start=segment.page_start,
                    page_end=segment.page_end,
                    char_count=len(window),
                    word_count=len(_WORD_RE.findall(window)),
                )
            )
            chunk_index += 1
    return chunk_payloads


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


def _build_chunk_context_header(publication: Publication) -> str:
    metadata_parts = [publication.title]
    authors = ", ".join(author.full_name for author in publication.authors.all())
    if authors:
        metadata_parts.append(f"Авторы: {authors}")
    publication_type = publication.publication_type.name if publication.publication_type else ""
    if publication_type:
        metadata_parts.append(f"Тип: {publication_type}")
    if publication.publication_subtype:
        metadata_parts.append(f"Подтип: {publication.publication_subtype.name}")
    keywords = ", ".join(keyword.name for keyword in publication.keywords.all())
    if keywords:
        metadata_parts.append(f"Ключевые слова: {keywords}")
    if publication.publication_year:
        metadata_parts.append(f"Год: {publication.publication_year}")
    return "\n".join(part for part in metadata_parts if part)


def build_publication_chunks(publication: Publication, extracted_text: str = "") -> list[ChunkPayload]:
    max_words = int(getattr(settings, "VECTOR_CHUNK_MAX_WORDS", 320))
    overlap_words = int(getattr(settings, "VECTOR_CHUNK_OVERLAP_WORDS", 40))
    max_chars = int(getattr(settings, "VECTOR_CHUNK_MAX_CHARS", 2200))

    segments: list[ExtractedSegment] = []
    if publication.file:
        try:
            file_name = publication.file.name
            if file_name and publication.file.storage.exists(file_name):
                segments = extract_segments_from_file(publication.file.path)
        except (FileNotFoundError, OSError, SuspiciousFileOperation, ValueError):
            segments = []

    if not segments:
        combined = build_search_document(publication, extracted_text=extracted_text)
        if combined:
            segments = [ExtractedSegment(text=combined)]

    raw_chunks = chunk_segments(segments, max_words=max_words, overlap_words=overlap_words, max_chars=max_chars)
    if not raw_chunks:
        combined = build_search_document(publication, extracted_text=extracted_text)
        if combined:
            raw_chunks = [
                ChunkPayload(
                    chunk_index=0,
                    text=combined[:max_chars],
                    chunk_text=combined[:max_chars],
                    char_count=min(len(combined), max_chars),
                    word_count=len(_WORD_RE.findall(combined[:max_chars])),
                )
            ]

    header = _build_chunk_context_header(publication)
    payloads: list[ChunkPayload] = []
    for raw_chunk in raw_chunks:
        contextual_text = normalize_text(f"{header}\n\nФрагмент документа: {raw_chunk.text}" if header else raw_chunk.text)
        payloads.append(
            ChunkPayload(
                chunk_index=raw_chunk.chunk_index,
                text=raw_chunk.text,
                chunk_text=contextual_text,
                page_start=raw_chunk.page_start,
                page_end=raw_chunk.page_end,
                char_count=raw_chunk.char_count,
                word_count=raw_chunk.word_count,
            )
        )
    return payloads


def sync_publication_chunks(publication: Publication, chunk_payloads: list[ChunkPayload]) -> list[PublicationChunk]:
    publication.chunks.all().delete()
    chunk_objects = [
        PublicationChunk(
            publication=publication,
            chunk_index=payload.chunk_index,
            text=payload.text,
            page_start=payload.page_start,
            page_end=payload.page_end,
            char_count=payload.char_count,
            word_count=payload.word_count,
        )
        for payload in chunk_payloads
        if payload.text
    ]
    if not chunk_objects:
        return []
    created_objects = PublicationChunk.objects.bulk_create(chunk_objects)
    return list(created_objects)


def ingest_publication(publication: Publication, index_in_vector_store: bool = True) -> Publication:
    extracted_text = extract_text_from_publication_file(publication)
    if extracted_text:
        merged_contents = publication.contents.strip()
        if merged_contents and extracted_text not in merged_contents:
            publication.contents = f"{merged_contents}\n\n{extracted_text}".strip()
        elif not merged_contents:
            publication.contents = extracted_text
        publication.save(update_fields=["contents"])

    chunk_payloads = build_publication_chunks(publication, extracted_text=extracted_text)
    chunk_objects = sync_publication_chunks(publication, chunk_payloads)

    if index_in_vector_store and not publication.is_draft:
        service = VectorStoreService()
        service.replace_publication_chunks(publication=publication, chunks=chunk_objects)
    return publication
