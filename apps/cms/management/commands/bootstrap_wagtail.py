from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from apps.cms.models import AnnouncementIndexPage, HomePage


class Command(BaseCommand):
    help = "Create the initial Wagtail page tree if it does not exist."

    def _get_or_create_home_page(self, root: Page) -> Page:
        home = HomePage.objects.child_of(root).first()
        if home:
            return home

        existing_home = root.get_children().filter(slug="home").first()
        if existing_home:
            specific_home = existing_home.specific
            if not isinstance(specific_home, HomePage):
                self.stdout.write(
                    self.style.WARNING(
                        "A root page with slug 'home' already exists and will be reused. "
                        "It is not an instance of apps.cms.HomePage."
                    )
                )
            return specific_home

        home = HomePage(title="Главная", slug="home")
        root.add_child(instance=home)
        home.save_revision().publish()
        return home

    def _get_or_create_announcements_page(self, home: Page) -> Page:
        announcements = AnnouncementIndexPage.objects.child_of(home).first()
        if announcements:
            return announcements

        existing_announcements = home.get_children().filter(slug="announcements").first()
        if existing_announcements:
            specific_announcements = existing_announcements.specific
            if not isinstance(specific_announcements, AnnouncementIndexPage):
                self.stdout.write(
                    self.style.WARNING(
                        "A child page with slug 'announcements' already exists and will be reused. "
                        "It is not an instance of apps.cms.AnnouncementIndexPage."
                    )
                )
            return specific_announcements

        announcements = AnnouncementIndexPage(title="Объявления", slug="announcements")
        home.add_child(instance=announcements)
        announcements.save_revision().publish()
        return announcements

    def handle(self, *args, **options):
        root = Page.get_first_root_node()
        home = self._get_or_create_home_page(root)
        self._get_or_create_announcements_page(home)

        site, created = Site.objects.get_or_create(
            hostname="localhost",
            defaults={"root_page": home, "site_name": "Institutional Repository", "port": 8000},
        )
        if not created:
            site.root_page = home
            site.site_name = "Institutional Repository"
            site.port = 8000
            site.save()

        self.stdout.write(self.style.SUCCESS("Wagtail bootstrap completed."))
