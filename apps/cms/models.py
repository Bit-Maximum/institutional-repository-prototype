from datetime import date

from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.blocks import CharBlock, RichTextBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page


class HomePage(Page):
    hero_title = models.CharField(max_length=255, default="Институциональный репозиторий")
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("hero_title"),
        FieldPanel("body"),
    ]


class AnnouncementIndexPage(Page):
    intro = RichTextField(blank=True)
    subpage_types = ["cms.AnnouncementPage"]

    content_panels = Page.content_panels + [FieldPanel("intro")]


class AnnouncementPage(Page):
    published_at = models.DateField(default=date.today)
    is_pinned = models.BooleanField(default=False)
    body = StreamField(
        [
            ("heading", CharBlock(form_classname="title")),
            ("paragraph", RichTextBlock()),
        ],
        use_json_field=True,
        blank=True,
    )

    parent_page_types = ["cms.AnnouncementIndexPage"]

    content_panels = Page.content_panels + [
        FieldPanel("published_at"),
        FieldPanel("is_pinned"),
        FieldPanel("body"),
    ]
