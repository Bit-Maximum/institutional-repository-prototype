from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .models import Publication

PREVIEW_MAX_SIZE = (960, 1400)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


class PreviewGenerationError(RuntimeError):
    pass


class _Fonts:
    title: ImageFont.FreeTypeFont | ImageFont.ImageFont
    body: ImageFont.FreeTypeFont | ImageFont.ImageFont
    meta: ImageFont.FreeTypeFont | ImageFont.ImageFont
    badge: ImageFont.FreeTypeFont | ImageFont.ImageFont


def _load_font(name: str, size: int):
    try:
        return ImageFont.truetype(name, size=size)
    except Exception:
        return ImageFont.load_default()


def _get_fonts() -> _Fonts:
    fonts = _Fonts()
    fonts.title = _load_font("DejaVuSans-Bold.ttf", 40)
    fonts.body = _load_font("DejaVuSans.ttf", 26)
    fonts.meta = _load_font("DejaVuSans.ttf", 22)
    fonts.badge = _load_font("DejaVuSans-Bold.ttf", 20)
    return fonts


def _make_vertical_gradient(size: tuple[int, int], top_rgb: tuple[int, int, int], bottom_rgb: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, top_rgb)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * ratio) for i in range(3))
        draw.line((0, y, width, y), fill=color)
    return image


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    if not text:
        return 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return max(0, bbox[2] - bbox[0])


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    if not text:
        return []
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        probe = f"{current} {word}".strip()
        if _measure_text(draw, probe, font) <= max_width:
            current = probe
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
    if len(lines) < max_lines:
        lines.append(current)

    consumed = sum(len(line.split()) for line in lines)
    if consumed < len(words) and lines:
        tail = lines[-1]
        while tail and _measure_text(draw, f"{tail}…", font) > max_width:
            tail = " ".join(tail.split()[:-1])
        lines[-1] = f"{tail}…" if tail else "…"
    return lines[:max_lines]


def _placeholder_palette(publication: Publication) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    extension = (publication.file_extension or Path(getattr(publication.file, "name", "") or "").suffix.lower()).lower()
    publication_type = (publication.publication_type.name if publication.publication_type else "").lower()
    if extension == ".pdf":
        return (23, 52, 112), (44, 95, 181), (220, 232, 255)
    if extension == ".docx":
        return (28, 63, 133), (59, 130, 246), (226, 238, 255)
    if "учеб" in publication_type:
        return (52, 85, 146), (96, 136, 214), (234, 241, 255)
    if "науч" in publication_type:
        return (17, 64, 90), (14, 116, 144), (223, 248, 255)
    return (48, 66, 109), (91, 116, 178), (232, 238, 252)


def _draw_rounded_rectangle(base: Image.Image, xy, radius: int, fill, outline=None, width: int = 1):
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _render_placeholder(publication: Publication) -> tuple[bytes, str]:
    size = PREVIEW_MAX_SIZE
    top, bottom, accent = _placeholder_palette(publication)
    image = _make_vertical_gradient(size, top, bottom).convert("RGBA")
    draw = ImageDraw.Draw(image)
    fonts = _get_fonts()

    _draw_rounded_rectangle(image, (38, 42, 682, 918), 42, fill=(255, 255, 255, 28), outline=(255, 255, 255, 48), width=2)
    _draw_rounded_rectangle(image, (72, 88, 648, 180), 28, fill=(255, 255, 255, 34))
    _draw_rounded_rectangle(image, (72, 208, 648, 888), 34, fill=(255, 255, 255, 22))

    extension = (publication.file_extension or Path(getattr(publication.file, "name", "") or "").suffix.lower().lstrip(".")) or "FILE"
    badge_text = extension.upper()
    badge_bbox = draw.textbbox((0, 0), badge_text, font=fonts.badge)
    badge_width = (badge_bbox[2] - badge_bbox[0]) + 34
    _draw_rounded_rectangle(image, (94, 108, 94 + badge_width, 152), 18, fill=(255, 255, 255, 64), outline=(255, 255, 255, 92), width=1)
    draw.text((111, 117), badge_text, font=fonts.badge, fill=(245, 248, 255, 255))

    x = 94
    y = 238
    max_width = 532

    title_lines = _wrap_text(draw, publication.title or "Без названия", fonts.title, max_width, 5)
    for line in title_lines:
        draw.text((x, y), line, font=fonts.title, fill=(248, 250, 255, 255))
        y += 50

    y += 12
    metadata_parts = []
    if publication.publication_type:
        metadata_parts.append(str(publication.publication_type.name))
    if publication.publication_subtype:
        metadata_parts.append(str(publication.publication_subtype.name))
    if publication.publication_year:
        metadata_parts.append(str(publication.publication_year))
    if publication.language:
        metadata_parts.append(str(publication.language.name))
    metadata_text = " · ".join(part for part in metadata_parts if part)
    if metadata_text:
        meta_lines = _wrap_text(draw, metadata_text, fonts.meta, max_width, 3)
        for line in meta_lines:
            draw.text((x, y), line, font=fonts.meta, fill=(230, 239, 255, 235))
            y += 34
        y += 8

    authors = ", ".join(author.full_name for author in publication.authors.all()[:4])
    if authors:
        author_lines = _wrap_text(draw, authors, fonts.body, max_width, 3)
        for line in author_lines:
            draw.text((x, y), line, font=fonts.body, fill=(240, 245, 255, 220))
            y += 34
        y += 12

    contents = (publication.contents or "").strip()
    if contents:
        excerpt_lines = _wrap_text(draw, contents, fonts.body, max_width, 6)
        for line in excerpt_lines:
            draw.text((x, y), line, font=fonts.body, fill=(232, 238, 255, 198))
            y += 34

    draw.line((94, 834, 626, 834), fill=(255, 255, 255, 88), width=2)
    footer = "Institutional Repository Prototype"
    draw.text((94, 852), footer, font=fonts.meta, fill=(233, 241, 255, 212))

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse((492, -30, 760, 220), fill=(*accent, 42))
    overlay_draw.ellipse((-80, 704, 180, 972), fill=(255, 255, 255, 18))
    image = Image.alpha_composite(image, overlay)

    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue(), "generated_placeholder"


def _render_from_uploaded_image(publication: Publication) -> tuple[bytes, str]:
    publication.file.open("rb")
    try:
        with Image.open(publication.file) as image:
            prepared = image.convert("RGB")
            prepared.thumbnail(PREVIEW_MAX_SIZE, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            prepared.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue(), "uploaded_image"
    finally:
        publication.file.close()


def _render_from_pdf(publication: Publication) -> tuple[bytes, str]:
    try:
        import pypdfium2 as pdfium
    except Exception as exc:  # pragma: no cover - optional dependency fallback
        raise PreviewGenerationError("PDF preview dependency is unavailable") from exc

    document = pdfium.PdfDocument(publication.file.path)
    try:
        page = document[0]
        bitmap = page.render(scale=2.2)
        image = bitmap.to_pil().convert("RGB")
        image.thumbnail(PREVIEW_MAX_SIZE, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue(), "pdf_first_page"
    finally:
        try:
            page.close()
        except Exception:
            pass
        try:
            document.close()
        except Exception:
            pass


def render_publication_preview(publication: Publication) -> tuple[bytes, str]:
    file_name = getattr(publication.file, "name", "") or ""
    extension = Path(file_name).suffix.lower()
    if file_name and publication.file:
        if extension in IMAGE_EXTENSIONS:
            return _render_from_uploaded_image(publication)
        if extension == ".pdf":
            try:
                return _render_from_pdf(publication)
            except Exception:
                return _render_placeholder(publication)
    return _render_placeholder(publication)


@transaction.atomic
def ensure_publication_preview(publication: Publication, *, force: bool = False) -> bool:
    if not force and publication.preview_image and publication.preview_generated_at:
        return False

    preview_bytes, preview_kind = render_publication_preview(publication)
    filename_suffix = slugify(publication.title or f"publication-{publication.pk}") or f"publication-{publication.pk}"
    filename = f"publication-{publication.pk}-{filename_suffix[:48]}-preview.png"

    if publication.preview_image:
        try:
            publication.preview_image.delete(save=False)
        except Exception:
            pass

    publication.preview_image.save(filename, ContentFile(preview_bytes), save=False)
    publication.preview_kind = preview_kind
    publication.preview_generated_at = timezone.now()
    publication.save(update_fields=["preview_image", "preview_kind", "preview_generated_at"])
    return True


def ensure_publication_previews(publications: list[Publication] | tuple[Publication, ...], *, force: bool = False) -> None:
    for publication in publications:
        ensure_publication_preview(publication, force=force)
