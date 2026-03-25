from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.uploadedfile import UploadedFile
from docx import Document
from pypdf import PdfReader

from apps.publications.models import (
    Author,
    Keyword,
    Publication,
    PublicationChunk,
    PublicationLanguage,
    PublicationSubtype,
    PublicationType,
    ScientificSupervisor,
    TEXT_EXTRACTION_STATUS_CHOICES,
)
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
    source_kind: str = "fulltext"
    page_start: int | None = None
    page_end: int | None = None
    char_count: int = 0
    word_count: int = 0


@dataclass(slots=True)
class FileExtractionAnalysis:
    file_extension: str = ""
    status: str = "pending"
    notes: str = ""
    supported_format: bool = False
    has_extractable_text: bool = False
    extracted_text: str = ""
    raw_text: str = ""
    segments: list[ExtractedSegment] = field(default_factory=list)
    page_count: int | None = None


_WORD_RE = re.compile(r"\S+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WHITESPACE_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})(?!\d)")
_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]{3,}")
_FILENAME_SEPARATORS_RE = re.compile(r"[_\-]+")

CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_RE = re.compile(r"[A-Za-z]")
_REFERENCE_HEADING_RE = re.compile(
    r"^(references|bibliography|список литературы|литература|bibliographic references)",
    re.IGNORECASE,
)
_REFERENCE_LINE_RE = re.compile(r"(?m)^\s*(?:\[?\d+[\].)]|\d+\.)\s+")
_REFERENCE_SIGNAL_RE = re.compile(
    r"(?:et\s+al\.?|doi\s*[:/]|vol\.?\s*\d+|pp?\.\s*\d+|j bone joint surg|clin orthop|bmj\b|cochrane\b)",
    re.IGNORECASE,
)
_DOT_LEADER_RE = re.compile(r"\.{5,}")
_TOC_HEADING_RE = re.compile(r"^(?:содержание|оглавление|table of contents)\b", re.IGNORECASE)
_TOC_LINE_RE = re.compile(r"(?m)^\s*[^\n]{3,180}?\.{5,}\s*\d{1,4}\s*$")
_PAGE_NUMBER_LINE_RE = re.compile(r"(?m)^\s*[\divxlcdmIVXLCDM\.\-–— ]{1,12}\s*$")


def detect_script_kind(text: str) -> str:
    cyrillic = len(CYRILLIC_RE.findall(text or ""))
    latin = len(LATIN_RE.findall(text or ""))
    alpha = cyrillic + latin
    if alpha == 0:
        return "neutral"
    cyr_ratio = cyrillic / alpha
    lat_ratio = latin / alpha
    if cyr_ratio >= 0.7:
        return "cyrillic"
    if lat_ratio >= 0.7:
        return "latin"
    return "mixed"


def is_reference_heavy_text(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    lowered = normalized.lower()
    if _REFERENCE_HEADING_RE.search(lowered):
        return True
    year_hits = len(_YEAR_RE.findall(normalized))
    numbered_refs = len(_REFERENCE_LINE_RE.findall(text or ""))
    signals = len(_REFERENCE_SIGNAL_RE.findall(lowered))
    punctuation_density = sum(1 for char in normalized if char in ';:[]()') / max(len(normalized), 1)
    return (
        numbered_refs >= 2
        or (year_hits >= 4 and signals >= 1)
        or (year_hits >= 6 and punctuation_density > 0.05)
    )


def is_table_of_contents_text(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False

    lowered = normalized.lower()
    if _TOC_HEADING_RE.search(lowered):
        return True

    dot_leaders = len(_DOT_LEADER_RE.findall(text or ""))
    toc_lines = len(_TOC_LINE_RE.findall(text or ""))
    page_only_lines = len(_PAGE_NUMBER_LINE_RE.findall(text or ""))
    dot_ratio = sum(1 for char in (text or "") if char == ".") / max(len(text or ""), 1)

    return (
        toc_lines >= 2
        or (dot_leaders >= 3 and dot_ratio > 0.12)
        or (dot_leaders >= 2 and page_only_lines >= 1)
        or ("содержание" in lowered and dot_leaders >= 1)
    )


def chunk_index_quality(text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    alpha_count = sum(char.isalpha() for char in normalized)
    digit_count = sum(char.isdigit() for char in normalized)
    alpha_ratio = alpha_count / max(len(normalized), 1)
    digit_ratio = digit_count / max(len(normalized), 1)
    dot_ratio = sum(1 for char in (text or "") if char == ".") / max(len(text or ""), 1)
    quality = 1.0
    if alpha_ratio < 0.45:
        quality *= 0.65
    if digit_ratio > 0.18:
        quality *= 0.8
    if dot_ratio > 0.10:
        quality *= 0.45
    if is_table_of_contents_text(text):
        quality *= 0.05
    if is_reference_heavy_text(text):
        quality *= 0.12
    return max(0.0, min(1.0, quality))


SUPPORTED_TEXT_EXTENSIONS = {".pdf", ".docx"}
STATUS_LABELS = dict(TEXT_EXTRACTION_STATUS_CHOICES)
RUSSIAN_STOPWORDS = {
    "это", "как", "или", "для", "при", "над", "под", "без", "что", "его", "её", "она", "они",
    "мы", "вы", "из", "по", "на", "до", "от", "за", "не", "но", "а", "и", "в", "во", "с",
    "со", "к", "ко", "у", "о", "об", "обо", "ли", "же", "бы", "быть", "так", "также", "если",
    "или", "для", "при", "между", "через", "после", "перед", "когда", "где", "который", "которая",
    "которые", "данный", "данная", "данные", "издание", "документ", "материал", "работа", "система",
}
ENGLISH_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "about", "document", "publication",
    "system", "work", "study", "article", "guide", "manual", "report", "using", "used", "are", "was",
}


def normalize_text(value: str | None) -> str:
    return _WHITESPACE_RE.sub(" ", (value or "").strip())


def save_uploaded_file_to_temp(uploaded_file: UploadedFile) -> Path:
    temp_dir = Path(settings.MEDIA_ROOT) / "_tmp_upload_analysis"
    temp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as temp_handle:
        for chunk in uploaded_file.chunks():
            temp_handle.write(chunk)
        return Path(temp_handle.name)


def _table_texts(document: Document) -> list[str]:
    texts: list[str] = []
    for table in document.tables:
        for row in table.rows:
            row_parts = [normalize_text(cell.text) for cell in row.cells if normalize_text(cell.text)]
            if row_parts:
                texts.append(" | ".join(row_parts))
    return texts


def _extract_docx_lines(path: Path) -> tuple[list[str], str]:
    document = Document(str(path))
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text and paragraph.text.strip()]
    table_lines = _table_texts(document)
    lines.extend(table_lines)
    return lines, "\n".join(lines)


def _analyze_text_quality(text: str, *, page_count: int | None = None) -> tuple[bool, str]:
    normalized = normalize_text(text)
    char_threshold = int(getattr(settings, "INGESTION_MIN_TEXT_CHARS", 120))
    word_threshold = int(getattr(settings, "INGESTION_MIN_TEXT_WORDS", 25))
    char_count = len(normalized)
    word_count = len(_WORD_RE.findall(normalized))

    if char_count >= char_threshold and word_count >= word_threshold:
        return True, ""

    if page_count and page_count > 0:
        return (
            False,
            f"Извлечённого текста недостаточно для полноценной индексации ({word_count} слов на {page_count} стр.). "
            "Документ обработан в режиме metadata-only.",
        )
    return (
        False,
        f"Извлечённого текста недостаточно для полноценной индексации ({word_count} слов). "
        "Документ обработан в режиме metadata-only.",
    )


def analyze_publication_file(file_path: str | Path, *, original_name: str | None = None) -> FileExtractionAnalysis:
    path = Path(file_path)
    suffix = path.suffix.lower()
    analysis = FileExtractionAnalysis(file_extension=suffix)

    if not path.exists():
        analysis.status = "metadata_only_missing"
        analysis.notes = "Файл не найден в файловом хранилище. Для поиска будут использованы только метаданные."
        return analysis

    if suffix not in SUPPORTED_TEXT_EXTENSIONS:
        analysis.status = "metadata_only_unsupported"
        analysis.notes = (
            f"Формат {suffix or 'без расширения'} не поддерживается для автоматического извлечения текста. "
            "Для поиска будут использованы только введённые метаданные."
        )
        return analysis

    analysis.supported_format = True

    try:
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            analysis.page_count = len(reader.pages)
            raw_pages: list[str] = []
            segments: list[ExtractedSegment] = []
            for page_number, page in enumerate(reader.pages, start=1):
                raw_page_text = (page.extract_text() or "").strip()
                normalized_page_text = normalize_text(raw_page_text)
                if raw_page_text:
                    raw_pages.append(raw_page_text)
                if normalized_page_text:
                    segments.append(ExtractedSegment(text=normalized_page_text, page_start=page_number, page_end=page_number))
            analysis.raw_text = "\n\n".join(raw_pages).strip()
            analysis.extracted_text = "\n".join(segment.text for segment in segments if segment.text).strip()
            analysis.segments = segments
        elif suffix == ".docx":
            lines, raw_text = _extract_docx_lines(path)
            normalized_lines = [normalize_text(line) for line in lines if normalize_text(line)]
            analysis.raw_text = raw_text.strip()
            analysis.extracted_text = "\n\n".join(normalized_lines).strip()
            analysis.segments = [ExtractedSegment(text=analysis.extracted_text)] if analysis.extracted_text else []
    except Exception as exc:  # pragma: no cover - defensive fallback for malformed files
        analysis.status = "metadata_only_error"
        analysis.notes = (
            f"Не удалось автоматически извлечь текст ({exc.__class__.__name__}). "
            "Для поиска будут использованы только метаданные."
        )
        return analysis

    has_text, note = _analyze_text_quality(analysis.extracted_text, page_count=analysis.page_count)
    if has_text:
        analysis.status = "fulltext"
        analysis.has_extractable_text = True
        return analysis

    analysis.status = "metadata_only_nontext"
    analysis.notes = note or (
        "В файле не обнаружен машиночитаемый текст. Вероятно, документ имеет сканированную или нетекстовую структуру."
    )
    analysis.segments = []
    analysis.extracted_text = ""
    return analysis


def extract_text_from_file(file_path: str | Path) -> str:
    return analyze_publication_file(file_path).extracted_text


def extract_text_from_publication_file(publication: Publication) -> str:
    return analyze_publication_for_ingestion(publication).extracted_text


def extract_segments_from_file(file_path: str | Path) -> list[ExtractedSegment]:
    return analyze_publication_file(file_path).segments


def analyze_publication_for_ingestion(publication: Publication) -> FileExtractionAnalysis:
    if not publication.file:
        return FileExtractionAnalysis(
            file_extension="",
            status="metadata_only_missing",
            notes="Файл не приложен. Для поиска будут использованы только метаданные.",
        )
    try:
        file_name = publication.file.name
        if not file_name or not publication.file.storage.exists(file_name):
            return FileExtractionAnalysis(
                file_extension=Path(file_name or "").suffix.lower(),
                status="metadata_only_missing",
                notes="Файл отсутствует в файловом хранилище. Для поиска будут использованы только метаданные.",
            )
        return analyze_publication_file(publication.file.path, original_name=file_name)
    except (FileNotFoundError, OSError, SuspiciousFileOperation, ValueError):
        return FileExtractionAnalysis(
            file_extension=Path(getattr(publication.file, "name", "") or "").suffix.lower(),
            status="metadata_only_error",
            notes="Файл недоступен для чтения. Для поиска будут использованы только метаданные.",
        )


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
                    source_kind="fulltext",
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
    publication_type = publication.publication_type.name if publication.publication_type else ""
    publication_subtype = publication.publication_subtype.name if publication.publication_subtype else ""
    publishers = ", ".join(publisher.name for publisher in publication.publishers.all())
    places = ", ".join(place.name for place in publication.publication_places.all())
    parts = [
        publication.title,
        authors,
        supervisors,
        publication_type,
        publication_subtype,
        publication.contents,
        publication.grif_text,
        publication.grant_text,
        keyword_text,
        publishers,
        places,
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
    if publication.language:
        metadata_parts.append(f"Язык: {publication.language.name}")
    keywords = ", ".join(keyword.name for keyword in publication.keywords.all())
    if keywords:
        metadata_parts.append(f"Ключевые слова: {keywords}")
    if publication.publication_year:
        metadata_parts.append(f"Год: {publication.publication_year}")
    return "\n".join(part for part in metadata_parts if part)


def build_publication_chunks(
    publication: Publication,
    analysis: FileExtractionAnalysis | None = None,
    extracted_text: str = "",
) -> list[ChunkPayload]:
    max_words = int(getattr(settings, "VECTOR_CHUNK_MAX_WORDS", 320))
    overlap_words = int(getattr(settings, "VECTOR_CHUNK_OVERLAP_WORDS", 40))
    max_chars = int(getattr(settings, "VECTOR_CHUNK_MAX_CHARS", 2200))

    analysis = analysis or analyze_publication_for_ingestion(publication)
    segments = analysis.segments if analysis and analysis.has_extractable_text else []
    fulltext = extracted_text or analysis.extracted_text

    raw_chunks = chunk_segments(segments, max_words=max_words, overlap_words=overlap_words, max_chars=max_chars)
    min_quality = float(getattr(settings, "VECTOR_CHUNK_MIN_INDEX_QUALITY", 0.28))
    filtered_chunks = [chunk for chunk in raw_chunks if chunk_index_quality(chunk.text) >= min_quality]
    raw_chunks = filtered_chunks or raw_chunks

    if not raw_chunks:
        combined = build_search_document(publication, extracted_text=fulltext)
        combined_chunks = _split_text_into_windows(combined, max_words=max_words, overlap_words=overlap_words, max_chars=max_chars) if combined else []
        if not combined_chunks and combined:
            combined_chunks = [combined[:max_chars]]
        raw_chunks = [
            ChunkPayload(
                chunk_index=index,
                text=chunk_text,
                chunk_text=chunk_text,
                source_kind="metadata",
                char_count=len(chunk_text),
                word_count=len(_WORD_RE.findall(chunk_text)),
            )
            for index, chunk_text in enumerate(combined_chunks)
            if chunk_text
        ]

    header = _build_chunk_context_header(publication)
    payloads: list[ChunkPayload] = []
    for raw_chunk in raw_chunks:
        prefix = "Фрагмент документа" if raw_chunk.source_kind == "fulltext" else "Метаданные документа"
        contextual_text = normalize_text(f"{header}\n\n{prefix}: {raw_chunk.text}" if header else raw_chunk.text)
        payloads.append(
            ChunkPayload(
                chunk_index=raw_chunk.chunk_index,
                text=raw_chunk.text,
                chunk_text=contextual_text,
                source_kind=raw_chunk.source_kind,
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
            source_kind=payload.source_kind,
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
    analysis = analyze_publication_for_ingestion(publication)
    update_fields = ["file_extension", "text_extraction_status", "text_extraction_notes", "has_extracted_text"]
    publication.file_extension = analysis.file_extension
    publication.text_extraction_status = analysis.status
    publication.text_extraction_notes = analysis.notes
    publication.has_extracted_text = analysis.has_extractable_text
    publication.save(update_fields=update_fields)

    chunk_payloads = build_publication_chunks(publication, analysis=analysis, extracted_text=analysis.extracted_text)
    chunk_objects = sync_publication_chunks(publication, chunk_payloads)

    if index_in_vector_store and not publication.is_draft:
        service = VectorStoreService()
        service.replace_publication_chunks(publication=publication, chunks=chunk_objects)
    return publication


# --- Metadata suggestion helpers -------------------------------------------------

def _normalize_for_match(text: str) -> str:
    return normalize_text(text).lower().replace("ё", "е")


def _candidate_title_lines(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line and line.strip()]


def _score_title_candidate(candidate: str) -> float:
    normalized = normalize_text(candidate)
    if not normalized:
        return -1.0
    score = 0.0
    words = normalized.split()
    word_count = len(words)
    if 2 <= word_count <= 18:
        score += 2.0
    if 12 <= len(normalized) <= 180:
        score += 2.0
    if sum(ch.isalpha() for ch in normalized) / max(len(normalized), 1) > 0.6:
        score += 1.5
    if not normalized.endswith(('.', ':', ';')):
        score += 0.5
    if normalized.isupper():
        score -= 0.3
    if normalized.lower().startswith(("министерство", "федеральное", "университет", "кафедра")):
        score -= 0.8
    if _YEAR_RE.search(normalized):
        score -= 0.5
    return score


def _humanize_filename(filename: str) -> str:
    stem = Path(filename).stem
    stem = _FILENAME_SEPARATORS_RE.sub(" ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def suggest_title_from_text(raw_text: str, filename: str = "") -> str:
    candidates = _candidate_title_lines(raw_text)[:25]
    if candidates:
        best = max(candidates, key=_score_title_candidate)
        if _score_title_candidate(best) >= 2.5:
            return normalize_text(best)
    humanized = _humanize_filename(filename)
    return normalize_text(humanized)


def suggest_year_from_text(raw_text: str, filename: str = "") -> int | None:
    matches = [int(value) for value in _YEAR_RE.findall(f"{filename}\n{raw_text}")]
    if not matches:
        return None
    current_year = 2100
    plausible = [value for value in matches if 1900 <= value <= current_year]
    if not plausible:
        return None
    counts = Counter(plausible)
    return counts.most_common(1)[0][0]


def suggest_language_from_text(text: str) -> PublicationLanguage | None:
    normalized = text or ""
    cyrillic_count = sum(1 for char in normalized if "а" <= char.lower() <= "я" or char.lower() == "ё")
    latin_count = sum(1 for char in normalized if "a" <= char.lower() <= "z")
    if cyrillic_count == 0 and latin_count == 0:
        return None
    target = "рус" if cyrillic_count >= latin_count else "англ"
    return PublicationLanguage.objects.filter(name__icontains=target).order_by("name").first()


def _find_existing_people_matches(text: str, model, field_name: str, limit: int = 5) -> list[int]:
    normalized_text = _normalize_for_match(text)
    matched_ids: list[int] = []
    for obj in model.objects.all().only("id", field_name):
        candidate = _normalize_for_match(getattr(obj, field_name, ""))
        if candidate and candidate in normalized_text:
            matched_ids.append(obj.pk)
        if len(matched_ids) >= limit:
            break
    return matched_ids


def _find_keyword_matches(text: str, limit: int = 8) -> list[int]:
    normalized_text = _normalize_for_match(text)
    matched_ids: list[int] = []
    for keyword in Keyword.objects.all().only("id", "name"):
        candidate = _normalize_for_match(keyword.name)
        if candidate and candidate in normalized_text:
            matched_ids.append(keyword.pk)
        if len(matched_ids) >= limit:
            break
    return matched_ids


def _pick_best_subtype(text: str) -> PublicationSubtype | None:
    normalized_text = _normalize_for_match(text)
    best_subtype = None
    best_score = 0
    for subtype in PublicationSubtype.objects.select_related("publication_type").all():
        name = _normalize_for_match(subtype.name)
        if not name:
            continue
        tokens = [token for token in re.split(r"\W+", name) if len(token) >= 4]
        if not tokens:
            tokens = [name]
        score = sum(1 for token in tokens if token in normalized_text)
        if name in normalized_text:
            score += 2
        if score > best_score:
            best_score = score
            best_subtype = subtype
    return best_subtype if best_score > 0 else None


def _pick_best_type(text: str) -> PublicationType | None:
    normalized_text = _normalize_for_match(text)
    best_type = None
    best_score = 0
    for publication_type in PublicationType.objects.all():
        name = _normalize_for_match(publication_type.name)
        if not name:
            continue
        tokens = [token for token in re.split(r"\W+", name) if len(token) >= 4]
        if not tokens:
            tokens = [name]
        score = sum(1 for token in tokens if token in normalized_text)
        if name in normalized_text:
            score += 1
        if score > best_score:
            best_score = score
            best_type = publication_type
    return best_type if best_score > 0 else None


def _suggest_contents_preview(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    max_chars = int(getattr(settings, "UPLOAD_PREFILL_CONTENTS_MAX_CHARS", 700))
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _suggest_keywords_from_frequency(text: str, limit: int = 8) -> list[str]:
    normalized = _normalize_for_match(text)
    stopwords = RUSSIAN_STOPWORDS | ENGLISH_STOPWORDS
    counts = Counter(
        token
        for token in _TOKEN_RE.findall(normalized)
        if token not in stopwords and not token.isdigit() and len(token) >= 4
    )
    return [token for token, _ in counts.most_common(limit)]


def generate_metadata_prefill(path: str | Path, filename: str = "") -> dict[str, Any]:
    analysis = analyze_publication_file(path, original_name=filename)
    search_text = analysis.raw_text or analysis.extracted_text or _humanize_filename(filename)
    title = suggest_title_from_text(analysis.raw_text or analysis.extracted_text, filename=filename)
    year = suggest_year_from_text(search_text, filename=filename)
    language = suggest_language_from_text(search_text)
    subtype = _pick_best_subtype(f"{title}\n{search_text}")
    publication_type = subtype.publication_type if subtype else _pick_best_type(f"{title}\n{search_text}")

    author_ids = _find_existing_people_matches(search_text, Author, "full_name")
    supervisor_ids = _find_existing_people_matches(
        search_text,
        ScientificSupervisor,
        "full_name",
    )
    keyword_ids = _find_keyword_matches(f"{title}\n{search_text}")
    keyword_names = [
        keyword.name
        for keyword in Keyword.objects.filter(pk__in=keyword_ids)
    ]
    if not keyword_names:
        keyword_names = _suggest_keywords_from_frequency(f"{title}\n{search_text}")

    selected_field_names = [
        name
        for name, value in {
            "title": title,
            "publication_year": year,
            "language": getattr(language, "pk", None),
            "publication_subtype": getattr(subtype, "pk", None),
            "authors": author_ids,
            "scientific_supervisors": supervisor_ids,
            "keywords": keyword_ids,
            "contents": _suggest_contents_preview(search_text),
        }.items()
        if value not in (None, "", [])
    ]

    return {
        "status": analysis.status,
        "status_label": STATUS_LABELS.get(analysis.status, analysis.status),
        "notes": analysis.notes,
        "supported_format": analysis.supported_format,
        "has_extractable_text": analysis.has_extractable_text,
        "file_extension": analysis.file_extension,
        "page_count": analysis.page_count,
        "title_candidate": title,
        "keyword_name_suggestions": keyword_names,
        "selected_field_names": selected_field_names,
        "field_values": {
            "title": title,
            "publication_year": year,
            "language": getattr(language, "pk", None),
            "publication_subtype": getattr(subtype, "pk", None),
            "publication_type_label": getattr(publication_type, "name", ""),
            "authors": author_ids,
            "scientific_supervisors": supervisor_ids,
            "keywords": keyword_ids,
            "contents": _suggest_contents_preview(search_text),
        },
    }


def generate_metadata_prefill_from_upload(uploaded_file: UploadedFile) -> dict[str, Any]:
    temp_path = save_uploaded_file_to_temp(uploaded_file)
    try:
        return generate_metadata_prefill(temp_path, filename=uploaded_file.name or "")
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
