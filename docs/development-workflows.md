# Локальная разработка и рабочие сценарии

## 1. Первый запуск

```bash
docker compose up -d
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py bootstrap_wagtail
uv run python manage.py ensure_milvus_collection
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

## 2. Когда нужен `collectstatic`

### Обычно не обязателен
Если:
- `DEBUG=True`;
- вы просто запускаете проект локально через `runserver`;
- правите шаблоны и большую часть CSS в dev-режиме.

### Нужен
Если:
- вы тестируете production-like режим;
- используете WhiteNoise / `STATIC_ROOT`;
- в браузере явно осталась старая статика;
- после замены архива нужно убедиться, что собрана актуальная версия CSS/JS.

Команда:

```bash
uv run python manage.py collectstatic
```

## 3. Полезные ежедневные сценарии

### Подготовить CMS
```bash
uv run python manage.py bootstrap_wagtail
```

### Обновить Milvus-коллекцию
```bash
uv run python manage.py ensure_milvus_collection
```

### Прогреть модели поиска
```bash
uv run python manage.py warm_search_models
```

### Полностью переиндексировать публикации
```bash
uv run python manage.py reindex_publications --force
```

### Пересобрать превью
```bash
uv run python manage.py generate_publication_previews --force
```

## 4. Работа с миграциями

Обычный сценарий:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Если проект существенно менялся на уровне схемы и вы работаете на старой локальной БД, иногда проще пересоздать локальную БД, чем чинить устаревшую структуру вручную.

## 5. Работа со стилями и кэшем браузера

После заметных UI-изменений:
1. выполнить `collectstatic`;
2. перезапустить сервер;
3. в браузере сделать `Ctrl + F5`.

Это особенно важно, если CSS-файл уже был закеширован.

## 6. Отладка типовых проблем

### `collectstatic` пишет про дубли admin/js
Это ожидаемо для проекта с `django-unfold`, потому что часть файлов Django admin переопределяется пакетом `unfold`.

### Пустой или сломанный Wagtail admin
Не стоит переопределять базовые шаблоны Wagtail агрессивно. Для безопасной кастомизации лучше:
- менять branding точечно;
- подключать CSS через hook;
- не ломать базовую геометрию интерфейса.

### Не работает semantic/hybrid поиск
Проверьте по порядку:
1. доступен ли Milvus;
2. выполнен ли `ensure_milvus_collection`;
3. есть ли индексированные публикации;
4. не сбились ли переменные окружения модели и коллекции.

### Не видны превью
Проверьте:
- существует ли `preview_image` у публикаций;
- выполнялась ли команда `generate_publication_previews`;
- не был ли очищен `MEDIA_ROOT`.

## 7. Рекомендуемый порядок работы разработчика

1. Обновить ветку / исходники.
2. `uv sync`
3. `migrate`
4. При изменениях CMS — `bootstrap_wagtail`
5. При изменениях Milvus / pipeline — `ensure_milvus_collection`, `reindex_publications`
6. При изменениях превью — `generate_publication_previews --force`
7. При UI-изменениях — `collectstatic`, `Ctrl + F5`
