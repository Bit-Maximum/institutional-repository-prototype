from django.core.management.base import BaseCommand
from wagtail.models import Page, Site

from apps.cms.models import AnnouncementIndexPage, HomePage


class Command(BaseCommand):
    help = "Create the initial Wagtail page tree if it does not exist."

    def handle(self, *args, **options):
        root = Page.get_first_root_node()
        home = HomePage.objects.child_of(root).first()
        if not home:
            home = HomePage(title="Главная", slug="home")
            root.add_child(instance=home)
            home.save_revision().publish()

        announcements = AnnouncementIndexPage.objects.child_of(home).first()
        if not announcements:
            announcements = AnnouncementIndexPage(title="Объявления", slug="announcements")
            home.add_child(instance=announcements)
            announcements.save_revision().publish()

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
