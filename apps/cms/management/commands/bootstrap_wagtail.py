from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from apps.cms.models import AnnouncementIndexPage, AnnouncementPage, ContentIndexPage, ContentPage, HomePage


class Command(BaseCommand):
    help = "Create and synchronize the initial Wagtail page tree for the repository CMS."

    def _resolve_site_config(self) -> tuple[str, int]:
        admin_url = getattr(settings, "WAGTAILADMIN_BASE_URL", "http://localhost:8000") or "http://localhost:8000"
        parsed = urlparse(admin_url)
        hostname = parsed.hostname or "localhost"
        if parsed.port:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80 if parsed.scheme == "http" else 8000
        return hostname, port

    def _publish(self, page: Page) -> Page:
        page.save_revision().publish()
        return page.specific

    def _get_or_create_home_page(self, root: Page) -> HomePage:
        home = HomePage.objects.child_of(root).first()
        if home:
            updated = False
            if not home.title:
                home.title = "CMS-раздел"
                updated = True
            if not home.hero_title:
                home.hero_title = "Редакционный раздел институционального репозитория"
                updated = True
            if updated:
                self._publish(home)
            return home

        existing_home = root.get_children().filter(slug="home").first()
        if existing_home:
            specific_home = existing_home.specific
            if isinstance(specific_home, HomePage):
                changed = False
                if specific_home.title == "Welcome to your new Wagtail site!":
                    specific_home.title = "CMS-раздел"
                    changed = True
                if specific_home.hero_title in {"", "Welcome to your new Wagtail site!"}:
                    specific_home.hero_title = "Редакционный раздел институционального репозитория"
                    changed = True
                if not specific_home.search_description:
                    specific_home.search_description = "Редакционный раздел институционального репозитория."
                    changed = True
                if not specific_home.show_in_menus:
                    specific_home.show_in_menus = True
                    changed = True
                if changed:
                    return self._publish(specific_home)
                return specific_home

            changed = False
            if specific_home.title == "Welcome to your new Wagtail site!":
                specific_home.title = "CMS-раздел"
                changed = True
            if getattr(specific_home, "search_description", "") in {"", None}:
                specific_home.search_description = "Редакционный раздел институционального репозитория."
                changed = True
            if not getattr(specific_home, "show_in_menus", False):
                specific_home.show_in_menus = True
                changed = True
            if changed:
                specific_home.save()
            self.stdout.write(
                self.style.WARNING(
                    "A root page with slug 'home' already exists and will be reused. "
                    "It is not an instance of apps.cms.HomePage."
                )
            )
            return specific_home

        home = HomePage(
            title="CMS-раздел",
            slug="home",
            hero_title="Редакционный раздел институционального репозитория",
            body=(
                "<p>Этот раздел предназначен для публикации объявлений, редакционных материалов и "
                "дополнительных страниц, связанных с институциональным репозиторием.</p>"
            ),
            search_description="Редакционный раздел институционального репозитория.",
            show_in_menus=True,
        )
        root.add_child(instance=home)
        return self._publish(home)

    def _get_or_create_announcements_page(self, home: HomePage) -> AnnouncementIndexPage:
        announcements = AnnouncementIndexPage.objects.child_of(home).first()
        if announcements:
            updated = False
            if not announcements.intro:
                announcements.intro = (
                    "<p>Здесь публикуются новости проекта, объявления для пользователей и редакционные сообщения.</p>"
                )
                updated = True
            if updated:
                self._publish(announcements)
            return announcements

        existing = home.get_children().filter(slug="announcements").first()
        if existing:
            specific = existing.specific
            if isinstance(specific, AnnouncementIndexPage):
                return specific
            self.stdout.write(
                self.style.WARNING(
                    "A child page with slug 'announcements' already exists and will be reused. "
                    "It is not an instance of apps.cms.AnnouncementIndexPage."
                )
            )
            return specific

        announcements = AnnouncementIndexPage(
            title="Объявления",
            slug="announcements",
            intro="<p>Новости, объявления и редакционные публикации для посетителей и сотрудников.</p>",
            search_description="Каталог объявлений и новостей.",
            show_in_menus=True,
        )
        home.add_child(instance=announcements)
        return self._publish(announcements)

    def _get_or_create_content_index_page(self, home: HomePage) -> ContentIndexPage:
        content_index = ContentIndexPage.objects.child_of(home).first()
        if content_index:
            updated = False
            if not content_index.intro:
                content_index.intro = (
                    "<p>В этом разделе редакторы могут создавать собственные страницы: памятки, инструкции, "
                    "контакты, справочные материалы и самостоятельные тематические разделы.</p>"
                )
                updated = True
            if updated:
                self._publish(content_index)
            return content_index

        existing = home.get_children().filter(slug="pages").first()
        if existing:
            specific = existing.specific
            if isinstance(specific, ContentIndexPage):
                return specific
            self.stdout.write(
                self.style.WARNING(
                    "A child page with slug 'pages' already exists and will be reused. "
                    "It is not an instance of apps.cms.ContentIndexPage."
                )
            )
            return specific

        content_index = ContentIndexPage(
            title="Страницы редакции",
            slug="pages",
            intro=(
                "<p>Каталог гибких страниц редакционного раздела. Используйте его для материалов, "
                "которые не относятся к карточкам изданий или объявлениям.</p>"
            ),
            search_description="Каталог свободных редакторских страниц.",
            show_in_menus=True,
        )
        home.add_child(instance=content_index)
        return self._publish(content_index)

    def _get_or_create_content_page(self, parent: Page, *, title: str, slug: str, intro: str, body_html: str) -> ContentPage:
        existing = parent.get_children().filter(slug=slug).first()
        if existing:
            specific = existing.specific
            if isinstance(specific, ContentPage):
                return specific
            self.stdout.write(
                self.style.WARNING(
                    f"A child page with slug '{slug}' already exists under '{parent.title}' and will be reused."
                )
            )
            return specific

        body = [
            {
                "type": "paragraph",
                "value": body_html,
            }
        ]
        page = ContentPage(
            title=title,
            slug=slug,
            intro=intro,
            body=body,
            search_description=intro,
            show_in_menus=True,
        )
        parent.add_child(instance=page)
        return self._publish(page)

    def _ensure_default_content_pages(self, content_index: ContentIndexPage) -> None:
        defaults = [
            {
                "title": "О редакционном разделе",
                "slug": "about",
                "intro": "Краткая информация о назначении CMS-раздела и о том, как он связан с прототипом институционального репозитория.",
                "body_html": (
                    "<p>CMS-раздел используется для публикации объявлений, редакционных страниц и вспомогательных материалов, "
                    "которые расширяют основной прототип институционального репозитория.</p>"
                ),
            },
            {
                "title": "Как публиковать материалы",
                "slug": "publishing-guide",
                "intro": "Базовая памятка для редакторов: где создавать объявления, где вести свободные страницы и как организовывать контент.",
                "body_html": (
                    "<p>Используйте раздел <strong>Объявления</strong> для новостей и служебных публикаций, а раздел "
                    "<strong>Страницы редакции</strong> — для инструкций, контактов, регламентов и дополнительных разделов.</p>"
                ),
            },
            {
                "title": "Контакты редакции",
                "slug": "contacts",
                "intro": "Страница-заготовка для контактной информации редакторов и ответственных сотрудников.",
                "body_html": (
                    "<p>Заполните эту страницу актуальными адресами электронной почты, ссылками и сведениями "
                    "об ответственных редакторах.</p>"
                ),
            },
        ]
        for item in defaults:
            self._get_or_create_content_page(content_index, **item)

    def _ensure_welcome_announcement(self, announcements: AnnouncementIndexPage) -> None:
        if AnnouncementPage.objects.child_of(announcements).exists():
            return
        page = AnnouncementPage(
            title="Редакционный раздел готов к работе",
            slug="welcome",
            is_pinned=True,
            summary="Стартовая публикация, подтверждающая, что CMS-раздел и базовая структура Wagtail настроены.",
            body=[
                {
                    "type": "paragraph",
                    "value": (
                        "<p>Редакционный раздел настроен. Вы можете публиковать объявления, создавать новые страницы и "
                        "развивать самостоятельную CMS-ветку сайта без ручной сборки структуры с нуля.</p>"
                    ),
                },
                {
                    "type": "cards",
                    "value": [
                        {"eyebrow": "Объявления", "title": "Новости и анонсы", "text": "Публикуйте сообщения для пользователей и редакторов."},
                        {"eyebrow": "Страницы", "title": "Свободные разделы", "text": "Создавайте дополнительные страницы для инструкций и материалов."},
                    ],
                },
            ],
            search_description="Стартовая публикация редакционного раздела.",
            show_in_menus=False,
        )
        announcements.add_child(instance=page)
        self._publish(page)

    def _configure_site(self, home: HomePage) -> Site:
        hostname, port = self._resolve_site_config()
        site, _ = Site.objects.get_or_create(
            hostname=hostname,
            port=port,
            defaults={
                "root_page": home,
                "site_name": "Институциональный репозиторий — CMS",
                "is_default_site": True,
            },
        )
        Site.objects.exclude(pk=site.pk).filter(is_default_site=True).update(is_default_site=False)
        changed = False
        if site.root_page_id != home.id:
            site.root_page = home
            changed = True
        if site.site_name != "Институциональный репозиторий — CMS":
            site.site_name = "Институциональный репозиторий — CMS"
            changed = True
        if not site.is_default_site:
            site.is_default_site = True
            changed = True
        if changed:
            site.save()
        return site

    def handle(self, *args, **options):
        root = Page.get_first_root_node()
        home = self._get_or_create_home_page(root)
        announcements = self._get_or_create_announcements_page(home)
        content_index = self._get_or_create_content_index_page(home)
        self._ensure_default_content_pages(content_index)
        self._ensure_welcome_announcement(announcements)
        site = self._configure_site(home)
        self.stdout.write(self.style.SUCCESS(
            f"Wagtail bootstrap completed. Site '{site.hostname}:{site.port}' now points to '{home.title}'."
        ))
