from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.formats import date_format

from apps.collections_app.models import Collection, CollectionReaction
from apps.publications.models import Publication, PublicationChunk, PublicationUserEngagement
from apps.search.models import SearchQuery
from apps.users.models import User


def _safe_reverse(viewname: str) -> str | None:
    try:
        return reverse(viewname)
    except NoReverseMatch:
        return None


def _series_from_queryset(queryset, date_field: str, days: int = 7) -> tuple[list[dict], int]:
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)

    aggregated = {
        row["day"]: row["total"]
        for row in queryset.filter(**{f"{date_field}__date__gte": start_date})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by("day")
    }

    max_value = max(aggregated.values(), default=0)
    series: list[dict] = []
    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        value = int(aggregated.get(current_day, 0) or 0)
        height_pct = 0 if max_value == 0 else max(14, round((value / max_value) * 100))
        series.append(
            {
                "date": current_day,
                "label": date_format(current_day, "d E"),
                "weekday": date_format(current_day, "D"),
                "value": value,
                "height_pct": height_pct,
            }
        )

    return series, max_value


def _as_table(headers: list[str], rows: list[list[str]]) -> dict:
    return {
        "headers": headers,
        "rows": rows,
    }


def _build_admin_home_context() -> dict:
    total_publications = Publication.objects.count()
    total_users = User.objects.count()
    total_collections = Collection.objects.count()
    total_searches = SearchQuery.objects.count()

    summary_cards = [
        {
            "title": "Издания",
            "value": total_publications,
            "meta": "Каталог, загрузка и индексация публикаций",
        },
        {
            "title": "Пользователи",
            "value": total_users,
            "meta": "Аккаунты, роли и авторизация",
        },
        {
            "title": "Коллекции",
            "value": total_collections,
            "meta": "Пользовательские подборки и реакции",
        },
        {
            "title": "Поисковые запросы",
            "value": total_searches,
            "meta": "История поиска и сигналы для рекомендаций",
        },
    ]

    def item(title: str, description: str, list_viewname: str, add_viewname: str | None, count: int | None = None) -> dict | None:
        list_url = _safe_reverse(list_viewname)
        add_url = _safe_reverse(add_viewname) if add_viewname else None
        if not list_url:
            return None
        return {
            "title": title,
            "description": description,
            "list_url": list_url,
            "add_url": add_url,
            "count": count,
            "has_count": count is not None,
        }

    sections = [
        {
            "title": "Публикации и каталог",
            "description": "Основные сущности репозитория, карточки изданий и данные индексации.",
            "items": [
                item(
                    "Издания",
                    "Полные карточки публикаций, статусы, файлы и workflow публикации.",
                    "admin:publications_publication_changelist",
                    "admin:publications_publication_add",
                    total_publications,
                ),
                item(
                    "Фрагменты изданий",
                    "Чанки текста, используемые для семантического поиска и гибридной выдачи.",
                    "admin:publications_publicationchunk_changelist",
                    "admin:publications_publicationchunk_add",
                    PublicationChunk.objects.count(),
                ),
                item(
                    "Типы изданий",
                    "Справочник верхнеуровневых типов публикаций.",
                    "admin:publications_publicationtype_changelist",
                    "admin:publications_publicationtype_add",
                ),
                item(
                    "Подтипы изданий",
                    "Детализация типов публикаций для классификации каталога.",
                    "admin:publications_publicationsubtype_changelist",
                    "admin:publications_publicationsubtype_add",
                ),
                item(
                    "Языки изданий",
                    "Справочник языков публикаций.",
                    "admin:publications_publicationlanguage_changelist",
                    "admin:publications_publicationlanguage_add",
                ),
                item(
                    "Периодичность",
                    "Категории периодичности для журналов и серийных изданий.",
                    "admin:publications_publicationperiodicity_changelist",
                    "admin:publications_publicationperiodicity_add",
                ),
            ],
        },
        {
            "title": "Авторы, атрибуты и библиография",
            "description": "Справочники, через которые формируются связи many-to-many в карточках публикаций.",
            "items": [
                item(
                    "Авторы",
                    "Авторы публикаций и обратные связи с изданиями.",
                    "admin:publications_author_changelist",
                    "admin:publications_author_add",
                ),
                item(
                    "Научные руководители",
                    "Руководители, связанные с изданиями и работами.",
                    "admin:publications_scientificsupervisor_changelist",
                    "admin:publications_scientificsupervisor_add",
                ),
                item(
                    "Ключевые слова",
                    "Тематические дескрипторы и предметные рубрики.",
                    "admin:publications_keyword_changelist",
                    "admin:publications_keyword_add",
                ),
                item(
                    "Библиографии",
                    "Библиографические описания и связанные записи.",
                    "admin:publications_bibliography_changelist",
                    "admin:publications_bibliography_add",
                ),
                item(
                    "Издатели",
                    "Организации-издатели публикаций.",
                    "admin:publications_publisher_changelist",
                    "admin:publications_publisher_add",
                ),
                item(
                    "Места издания",
                    "Географические места публикации материалов.",
                    "admin:publications_publicationplace_changelist",
                    "admin:publications_publicationplace_add",
                ),
                item(
                    "Копирайты",
                    "Правообладатели и связи с публикациями.",
                    "admin:publications_copyright_changelist",
                    "admin:publications_copyright_add",
                ),
                item(
                    "Графические издания",
                    "Связанные графические и иллюстративные материалы.",
                    "admin:publications_graphicedition_changelist",
                    "admin:publications_graphicedition_add",
                ),
                item(
                    "Учёные степени",
                    "Справочник степеней для квалификационных работ.",
                    "admin:publications_academicdegree_changelist",
                    "admin:publications_academicdegree_add",
                ),
            ],
        },
        {
            "title": "Пользователи и активность",
            "description": "Управление аккаунтами, ролями, пользовательскими коллекциями и сигналами использования.",
            "items": [
                item(
                    "Пользователи",
                    "Учетные записи пользователей репозитория.",
                    "admin:users_user_changelist",
                    "admin:users_user_add",
                    total_users,
                ),
                item(
                    "Группы",
                    "Роли и разрешения для администраторов и операторов.",
                    "admin:auth_group_changelist",
                    "admin:auth_group_add",
                    Group.objects.count(),
                ),
                item(
                    "Коллекции",
                    "Подборки публикаций, созданные пользователями.",
                    "admin:collections_app_collection_changelist",
                    "admin:collections_app_collection_add",
                    total_collections,
                ),
                item(
                    "Реакции на коллекции",
                    "Лайки и другие социальные сигналы для пользовательских коллекций.",
                    "admin:collections_app_collectionreaction_changelist",
                    "admin:collections_app_collectionreaction_add",
                    CollectionReaction.objects.count(),
                ),
                item(
                    "История поиска",
                    "Поисковые запросы пользователей, используемые и для аналитики, и для рекомендаций.",
                    "admin:search_searchquery_changelist",
                    "admin:search_searchquery_add",
                    total_searches,
                ),
                item(
                    "Взаимодействия с изданиями",
                    "Просмотры и скачивания публикаций пользователями.",
                    "admin:publications_publicationuserengagement_changelist",
                    "admin:publications_publicationuserengagement_add",
                    PublicationUserEngagement.objects.count(),
                ),
            ],
        },
        {
            "title": "Быстрые переходы",
            "description": "Дополнительные разделы для повседневной работы администратора.",
            "items": [
                {
                    "title": "Статистика системы",
                    "description": "Сводные показатели, графики, популярные запросы и состояние индексации.",
                    "list_url": reverse("admin:repository_statistics"),
                    "add_url": None,
                    "count": None,
                    "has_count": False,
                },
                {
                    "title": "CMS-админка",
                    "description": "Управление страницами, новостями и контентом сайта через Wagtail.",
                    "list_url": "/cms-admin/",
                    "add_url": None,
                    "count": None,
                    "has_count": False,
                },
                {
                    "title": "Публичный сайт",
                    "description": "Быстрый переход к пользовательскому интерфейсу репозитория.",
                    "list_url": "/",
                    "add_url": None,
                    "count": None,
                    "has_count": False,
                },
            ],
        },
    ]

    normalized_sections = []
    for section in sections:
        items = [item for item in section["items"] if item]
        if items:
            normalized_sections.append({**section, "items": items, "item_count": len(items)})

    return {
        "admin_home_summary_cards": summary_cards,
        "admin_home_sections": normalized_sections,
    }


def _build_dashboard_highlights(
    *,
    coverage_pct: int,
    indexed_publications: int,
    total_publications: int,
    draft_publications: int,
    searches_last_week: int,
    uploads_last_week: int,
    views_total: int,
    downloads_total: int,
) -> list[dict]:
    coverage_variant = "success" if coverage_pct >= 80 else "warning" if coverage_pct >= 40 else "danger"
    draft_variant = "warning" if draft_publications else "success"
    activity_variant = "info" if searches_last_week or uploads_last_week else "warning"

    return [
        {
            "label": "Покрытие индексации",
            "value": f"{coverage_pct}%",
            "text": f"{indexed_publications} из {total_publications} изданий в индексе",
            "variant": coverage_variant,
        },
        {
            "label": "Черновики",
            "value": draft_publications,
            "text": "Материалы, ожидающие публикации",
            "variant": draft_variant,
        },
        {
            "label": "Активность за 7 дней",
            "value": f"{searches_last_week} / {uploads_last_week}",
            "text": "поиски / загрузки за неделю",
            "variant": activity_variant,
        },
        {
            "label": "Взаимодействия пользователей",
            "value": f"{views_total} / {downloads_total}",
            "text": "просмотры / скачивания",
            "variant": "primary",
        },
    ]


def build_dashboard_context() -> dict:
    try:
        today = timezone.localdate()
        start_date = today - timedelta(days=6)

        total_publications = Publication.objects.count()
        published_publications = Publication.objects.filter(is_draft=False).count()
        draft_publications = Publication.objects.filter(is_draft=True).count()
        indexed_publications = Publication.objects.filter(vector_indexed_at__isnull=False).count()
        total_chunks = PublicationChunk.objects.count()
        total_users = User.objects.count()
        total_collections = Collection.objects.count()
        total_searches = SearchQuery.objects.count()
        searches_last_week = SearchQuery.objects.filter(created_at__date__gte=start_date).count()
        uploads_last_week = Publication.objects.filter(uploaded_at__date__gte=start_date).count()
        views_total = PublicationUserEngagement.objects.aggregate(total=Sum("view_count")).get("total") or 0
        downloads_total = (
            PublicationUserEngagement.objects.aggregate(total=Sum("download_count")).get("total") or 0
        )

        coverage_pct = round((indexed_publications / total_publications) * 100) if total_publications else 0
        avg_chunks = round(total_chunks / indexed_publications, 1) if indexed_publications else 0

        search_series, search_series_max = _series_from_queryset(SearchQuery.objects.all(), "created_at")
        upload_series, upload_series_max = _series_from_queryset(Publication.objects.all(), "uploaded_at")

        top_queries_qs = (
            SearchQuery.objects.exclude(query_text="")
            .values("query_text")
            .annotate(total=Count("id"))
            .order_by("-total", "query_text")[:8]
        )
        top_queries_rows = [[row["query_text"], str(row["total"])] for row in top_queries_qs]

        publication_type_rows = [
            [row["publication_subtype__publication_type__name"], str(row["total"])]
            for row in Publication.objects.filter(publication_subtype__publication_type__isnull=False)
            .values("publication_subtype__publication_type__name")
            .annotate(total=Count("id"))
            .order_by("-total", "publication_subtype__publication_type__name")[:8]
        ]

        recent_publications_rows = [
            [
                publication.title,
                publication.publication_type.name if publication.publication_type else "—",
                publication.get_status_display(),
            ]
            for publication in Publication.objects.select_related(
                "publication_subtype__publication_type"
            ).order_by("-uploaded_at")[:6]
        ]

        top_publications_qs = (
            Publication.objects.annotate(
                total_views=Sum("user_engagements__view_count"),
                total_downloads=Sum("user_engagements__download_count"),
            )
            .filter(Q(total_views__gt=0) | Q(total_downloads__gt=0))
            .order_by("-total_views", "-total_downloads", "title")[:6]
        )
        active_publications_rows = [
            [
                publication.title,
                str(int(publication.total_views or 0)),
                str(int(publication.total_downloads or 0)),
            ]
            for publication in top_publications_qs
        ]

        quick_links = [
            {
                "title": "Издания",
                "href": "admin:publications_publication_changelist",
                "metric": total_publications,
            },
            {
                "title": "Пользователи",
                "href": "admin:users_user_changelist",
                "metric": total_users,
            },
            {
                "title": "Коллекции",
                "href": "admin:collections_app_collection_changelist",
                "metric": total_collections,
            },
            {
                "title": "Поисковые запросы",
                "href": "admin:search_searchquery_changelist",
                "metric": total_searches,
            },
        ]

        highlights = _build_dashboard_highlights(
            coverage_pct=coverage_pct,
            indexed_publications=indexed_publications,
            total_publications=total_publications,
            draft_publications=draft_publications,
            searches_last_week=searches_last_week,
            uploads_last_week=uploads_last_week,
            views_total=int(views_total),
            downloads_total=int(downloads_total),
        )

        return {
            "dashboard_highlights": highlights,
            "dashboard_stats": [
                {
                    "title": "Издания",
                    "value": total_publications,
                    "meta": f"Опубликовано: {published_publications} · Черновики: {draft_publications}",
                },
                {
                    "title": "Индексация",
                    "value": f"{coverage_pct}%",
                    "meta": f"Проиндексировано: {indexed_publications} · Фрагментов: {total_chunks}",
                },
                {
                    "title": "Пользователи",
                    "value": total_users,
                    "meta": f"Коллекций: {total_collections}",
                },
                {
                    "title": "Поиск за 7 дней",
                    "value": searches_last_week,
                    "meta": f"Всего запросов: {total_searches}",
                },
                {
                    "title": "Новые загрузки за 7 дней",
                    "value": uploads_last_week,
                    "meta": "Динамика загрузки контента в репозиторий",
                },
                {
                    "title": "Взаимодействия",
                    "value": views_total,
                    "meta": f"Просмотры: {views_total} · Скачивания: {downloads_total}",
                },
            ],
            "dashboard_quick_links": quick_links,
            "dashboard_search_series": search_series,
            "dashboard_search_series_max": search_series_max,
            "dashboard_upload_series": upload_series,
            "dashboard_upload_series_max": upload_series_max,
            "dashboard_top_queries_table": _as_table(["Запрос", "Количество"], top_queries_rows),
            "dashboard_publication_types_table": _as_table(
                ["Тип издания", "Количество"], publication_type_rows
            ),
            "dashboard_recent_publications_table": _as_table(
                ["Издание", "Тип", "Статус"], recent_publications_rows
            ),
            "dashboard_active_publications_table": _as_table(
                ["Издание", "Просмотры", "Скачивания"], active_publications_rows
            ),
            "dashboard_index_summary": {
                "indexed_publications": indexed_publications,
                "total_publications": total_publications,
                "coverage_pct": coverage_pct,
                "avg_chunks": avg_chunks,
                "published_publications": published_publications,
            },
        }
    except Exception as exc:  # pragma: no cover - defensive fallback for admin stats page
        return {
            "dashboard_error": str(exc),
            "dashboard_highlights": [],
            "dashboard_stats": [],
            "dashboard_quick_links": [],
            "dashboard_search_series": [],
            "dashboard_upload_series": [],
            "dashboard_top_queries_table": _as_table(["Запрос", "Количество"], []),
            "dashboard_publication_types_table": _as_table(["Тип издания", "Количество"], []),
            "dashboard_recent_publications_table": _as_table(["Издание", "Тип", "Статус"], []),
            "dashboard_active_publications_table": _as_table(["Издание", "Просмотры", "Скачивания"], []),
            "dashboard_index_summary": {
                "indexed_publications": 0,
                "total_publications": 0,
                "coverage_pct": 0,
                "avg_chunks": 0,
                "published_publications": 0,
            },
        }


def dashboard_callback(request, context):
    context.update(_build_admin_home_context())
    return context
