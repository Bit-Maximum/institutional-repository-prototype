from datetime import date

from django.db import models
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import (
    CharBlock,
    ChoiceBlock,
    ListBlock,
    RichTextBlock,
    StructBlock,
    TextBlock,
    URLBlock,
)
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageBlock
from wagtail.models import Page


CONTENT_STREAM_BLOCKS = [
    ("heading", CharBlock(form_classname="title", icon="title", label=_("Подзаголовок"))),
    (
        "paragraph",
        RichTextBlock(
            features=["bold", "italic", "link", "ol", "ul", "hr", "h3", "h4"],
            label=_("Текстовый блок"),
        ),
    ),
    (
        "image",
        ImageBlock(
            required=False,
            label=_("Изображение"),
        ),
    ),
    (
        "document",
        StructBlock(
            [
                ("title", CharBlock(required=False, label=_("Подпись"))),
                ("document", DocumentChooserBlock(label=_("Документ"))),
            ],
            icon="doc-full-inverse",
            label=_("Ссылка на документ"),
        ),
    ),
    (
        "embed",
        EmbedBlock(
            required=False,
            max_width=960,
            max_height=540,
            label=_("Встраиваемый медиа-блок"),
        ),
    ),
    (
        "callout",
        StructBlock(
            [
                ("eyebrow", CharBlock(required=False, label=_("Метка"))),
                ("title", CharBlock(label=_("Заголовок"))),
                ("text", TextBlock(label=_("Текст"))),
            ],
            icon="placeholder",
            label=_("Выделенный блок"),
        ),
    ),
    (
        "quote",
        StructBlock(
            [
                ("text", TextBlock(label=_("Цитата"))),
                ("attribution", CharBlock(required=False, label=_("Источник"))),
            ],
            icon="openquote",
            label=_("Цитата"),
        ),
    ),
    (
        "buttons",
        ListBlock(
            StructBlock(
                [
                    ("label", CharBlock(label=_("Подпись кнопки"))),
                    ("url", URLBlock(label=_("Ссылка"))),
                    (
                        "style",
                        ChoiceBlock(
                            choices=[
                                ("primary", _("Основная")),
                                ("secondary", _("Вторичная")),
                            ],
                            default="primary",
                            label=_("Стиль"),
                        ),
                    ),
                ],
                icon="link",
                label=_("Кнопка"),
            ),
            icon="link",
            label=_("Ряд кнопок"),
        ),
    ),
    (
        "cards",
        ListBlock(
            StructBlock(
                [
                    ("eyebrow", CharBlock(required=False, label=_("Метка"))),
                    ("title", CharBlock(label=_("Заголовок"))),
                    ("text", TextBlock(required=False, label=_("Текст карточки"))),
                ],
                icon="placeholder",
                label=_("Карточка"),
            ),
            icon="list-ul",
            label=_("Сетка карточек"),
        ),
    ),
]


def _stream_summary(stream_value, *, limit: int = 220) -> str:
    if not stream_value:
        return ""

    fragments: list[str] = []
    for block in stream_value:
        value = block.value
        if block.block_type == "paragraph":
            fragments.append(strip_tags(str(value)))
        elif block.block_type == "callout":
            fragments.append(str(value.get("text", "")))
        elif block.block_type == "quote":
            fragments.append(str(value.get("text", "")))
        elif block.block_type == "cards":
            for card in value[:2]:
                fragments.append(str(card.get("text", "")))
        elif block.block_type == "document":
            fragments.append(str(value.get("title", "")))
        if " ".join(fragments).strip():
            break
    return Truncator(" ".join(fragment for fragment in fragments if fragment).strip()).chars(limit)


class HomePage(Page):
    hero_title = models.CharField(max_length=255, default="Редакционный раздел")
    body = RichTextField(blank=True)

    subpage_types = ["cms.AnnouncementIndexPage", "cms.ContentIndexPage"]
    page_description = _("Корневая страница CMS-раздела, из которой редакторы ведут объявления и дополнительные страницы.")

    content_panels = Page.content_panels + [
        FieldPanel("hero_title"),
        FieldPanel("body"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        child_pages = list(self.get_children().live().public().specific())
        announcement_index = next(
            (page for page in child_pages if isinstance(page, AnnouncementIndexPage)),
            None,
        )
        content_index = next(
            (page for page in child_pages if isinstance(page, ContentIndexPage)),
            None,
        )
        editorial_pages = []
        if content_index:
            editorial_pages = list(content_index.get_children().live().public().specific())[:6]
        context["announcement_index"] = announcement_index
        context["content_index"] = content_index
        context["editorial_pages"] = editorial_pages
        context["latest_announcements"] = AnnouncementPage.objects.live().public().order_by(
            "-is_pinned", "-published_at", "-first_published_at"
        )[:5]
        return context


class AnnouncementIndexPage(Page):
    intro = RichTextField(blank=True)
    subpage_types = ["cms.AnnouncementPage"]
    parent_page_types = ["cms.HomePage"]
    page_description = _("Каталог объявлений, новостей и редакционных публикаций.")

    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        queryset = AnnouncementPage.objects.live().public().descendant_of(self).order_by(
            "-is_pinned", "-published_at", "-first_published_at"
        )
        content_index = ContentIndexPage.objects.live().public().child_of(self.get_parent()).first()
        related_pages = []
        if content_index:
            related_pages = list(content_index.get_children().live().public().specific())[:4]
        context["pinned_announcements"] = queryset.filter(is_pinned=True)[:3]
        context["announcements"] = queryset
        context["content_index"] = content_index
        context["related_pages"] = related_pages
        return context


class AnnouncementPage(Page):
    published_at = models.DateField(default=date.today)
    is_pinned = models.BooleanField(default=False)
    summary = models.TextField(blank=True)
    body = StreamField(CONTENT_STREAM_BLOCKS, use_json_field=True, blank=True)

    parent_page_types = ["cms.AnnouncementIndexPage"]
    subpage_types = []
    page_description = _("Гибкая страница объявления для новостей, анонсов и служебных публикаций.")

    content_panels = Page.content_panels + [
        FieldPanel("published_at"),
        FieldPanel("is_pinned"),
        FieldPanel("summary"),
        FieldPanel("body"),
    ]

    @property
    def summary_text(self) -> str:
        if self.summary:
            return self.summary
        if self.search_description:
            return self.search_description
        return _stream_summary(self.body, limit=240)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["more_announcements"] = (
            AnnouncementPage.objects.live()
            .public()
            .descendant_of(self.get_parent())
            .exclude(pk=self.pk)
            .order_by("-is_pinned", "-published_at", "-first_published_at")[:4]
        )
        return context


class ContentIndexPage(Page):
    intro = RichTextField(blank=True)

    parent_page_types = ["cms.HomePage"]
    subpage_types = ["cms.ContentPage"]
    page_description = _("Каталог свободных редакторских страниц: справка, контакты, регламенты и новые разделы сайта.")

    content_panels = Page.content_panels + [FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["pages"] = list(self.get_children().live().public().specific())
        return context


class ContentPage(Page):
    intro = models.TextField(blank=True)
    body = StreamField(CONTENT_STREAM_BLOCKS, use_json_field=True, blank=True)

    parent_page_types = ["cms.ContentIndexPage", "cms.ContentPage"]
    subpage_types = ["cms.ContentPage"]
    page_description = _("Гибкая редакторская страница для новых разделов сайта, памяток и материалов вне логики прототипа.")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("body"),
    ]

    @property
    def summary_text(self) -> str:
        if self.intro:
            return Truncator(self.intro).chars(220)
        if self.search_description:
            return self.search_description
        return _stream_summary(self.body, limit=220)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["child_pages"] = list(self.get_children().live().public().specific())
        context["sibling_pages"] = [
            sibling for sibling in self.get_siblings(inclusive=False).live().public().specific()
            if isinstance(sibling, ContentPage)
        ][:5]
        return context
