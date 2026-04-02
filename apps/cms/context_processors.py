from __future__ import annotations

from wagtail.models import Site

from .models import AnnouncementIndexPage, ContentIndexPage, HomePage


def cms_context(request):
    try:
        site = Site.find_for_request(request)
    except Exception:
        site = None

    cms_home_page = None
    cms_announcements_page = None
    cms_content_index_page = None

    if site:
        root_page = site.root_page.specific
        if isinstance(root_page, HomePage):
            cms_home_page = root_page
            cms_announcements_page = AnnouncementIndexPage.objects.live().public().child_of(root_page).first()
            cms_content_index_page = ContentIndexPage.objects.live().public().child_of(root_page).first()

    return {
        'cms_home_page': cms_home_page,
        'cms_announcements_page': cms_announcements_page,
        'cms_content_index_page': cms_content_index_page,
    }
