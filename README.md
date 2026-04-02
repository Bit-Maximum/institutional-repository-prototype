# Institutional Repository Prototype

Прототип институционального репозитория, разработанный в рамках ВКР «Разработка институционального репозитория с использованием интеллектуального анализа текстов».

Проект объединяет:
- каталог электронных изданий с расширенными метаданными;
- keyword / semantic / hybrid поиск;
- хранение и переиндексацию фрагментов документов в Milvus;
- персональные коллекции и рекомендации;
- публичный интерфейс с переключаемыми глобальными стилями и темами;
- CMS-ветку на Wagtail для объявлений и редакторских страниц;
- расширенную административную часть на Django admin + django-unfold.

## Ключевые возможности

### Публичный сайт
- главная страница-витрина с новыми поступлениями, коллекциями, объявлениями и поиском;
- каталог изданий и детальные карточки;
- search page с режимами `keyword`, `semantic`, `hybrid`;
- расширенные фильтры с мультивыбором и поиском по значениям;
- объяснение, почему результат попал в выдачу;
- пользовательские коллекции, рекомендации, история поиска;
- переключение языка интерфейса и светлой/тёмной темы;
- поддержка глобальных UI-стилей, управляемых из админки.

### Редакторский и административный контур
- удобный редактор издания / черновика с прогрессом заполнения;
- загрузка исходного файла, автопредзаполнение метаданных и ручная загрузка превью;
- Django admin для справочников, изданий, коллекций, статистики и технического управления;
- Wagtail CMS для объявлений и свободных редакторских страниц.

### Интеллектуальный поиск и индексация
- извлечение текста из PDF и DOCX;
- chunk-based индексация публикаций;
- dense + sparse retrieval на `BAAI/bge-m3`;
- опциональный rerank на `BAAI/bge-reranker-v2-m3`;
- bulk reindex, warmup и benchmark-команды.

## Технологический стек

- Python 3.13
- Django 5.2
- Wagtail 7
- django-unfold
- PostgreSQL
- Milvus 2.6
- uv
- Hugging Face / FlagEmbedding / PyTorch
- WhiteNoise

## Архитектура проекта

```text
apps/
  core/             общие страницы, dashboard, health-check
  users/            регистрация, аутентификация, профиль, предпочтения
  publications/     издания, черновики, редактор изданий, превью
  collections_app/  пользовательские коллекции и работа с ними
  search/           поиск, explain-блоки, рекомендации, история
  ingestion/        извлечение текста и prefill метаданных
  vector_store/     Milvus, reindex, warmup, embeddings
  cms/              Wagtail-страницы, bootstrap CMS-структуры
  ui/               глобальные стили интерфейса, темы, локализация UI

config/
  settings/         base / local / production настройки
  urls.py           корневые маршруты

docs/
  architecture.md
  development-workflows.md
  search-and-indexing.md
  ui-extension-guide.md
  cms-guide.md
  content-editor-guide.md
```

Подробнее по архитектуре: [docs/architecture.md](docs/architecture.md)

## Основные маршруты

- `/` — главная страница прототипа
- `/publications/` — каталог изданий
- `/publications/drafts/` — список черновиков (для редакторов)
- `/search/` — интеллектуальный поиск
- `/collections/` — каталог коллекций
- `/accounts/` — регистрация и вход
- `/admin/` — Django admin
- `/cms-admin/` — Wagtail admin
- `/pages/` — публичная CMS-ветка
- `/pages/announcements/` — объявления

## Быстрый старт

### 1. Поднять инфраструктуру

```bash
docker compose up -d
```

Docker Compose поднимает инфраструктурные сервисы для локальной разработки:
- PostgreSQL
- Milvus Standalone
- MinIO
- etcd

Само Django-приложение запускается локально через `uv`.

### 2. Подготовить окружение

```bash
cp .env.example .env
uv sync
```

### 3. Применить миграции и инициализировать проект

```bash
uv run python manage.py migrate
uv run python manage.py bootstrap_wagtail
uv run python manage.py ensure_milvus_collection
uv run python manage.py createsuperuser
```

### 4. Запустить приложение

```bash
uv run python manage.py runserver
```

### 5. Собрать статику при необходимости

Для обычной локальной разработки с `DEBUG=True` это часто не обязательно. Для production-like сценария или после заметных правок CSS/JS:

```bash
uv run python manage.py collectstatic
```

## Базовые команды проекта

### CMS
```bash
uv run python manage.py bootstrap_wagtail
```
Создаёт и синхронизирует базовую структуру Wagtail.

### Milvus и модели поиска
```bash
uv run python manage.py ensure_milvus_collection
uv run python manage.py warm_search_models
```

### Индексация
```bash
uv run python manage.py reindex_publications
uv run python manage.py reindex_publications --force
uv run python manage.py reindex_publications --recreate-collection
```

### Превью изданий
```bash
uv run python manage.py generate_publication_previews
uv run python manage.py generate_publication_previews --force
```

### Benchmark поиска
```bash
uv run python manage.py benchmark_search
```

Подробнее по поиску и индексации: [docs/search-and-indexing.md](docs/search-and-indexing.md)

## Переменные окружения

Минимальный набор для локальной разработки:

```env
DEBUG=True
SECRET_KEY=change-me
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgresql://repository:repository@localhost:5432/repository
MILVUS_URI=http://localhost:19530
WAGTAILADMIN_BASE_URL=http://localhost:8000
```

Дополнительные параметры поиска, индексации и рекомендаций уже описаны в `.env.example`.

## Как работает проект

### 1. Загрузка и публикация издания
1. Редактор создаёт запись издания или черновик.
2. Загружает файл, внешний URL и/или вручную заполняет метаданные.
3. Система пытается извлечь текст и предзаполнить часть полей.
4. Редактор может загрузить ручное превью либо использовать автогенерацию.
5. После публикации запись становится доступна в каталоге.
6. Команда/сигнал индексации подготавливает chunk-данные для поиска.

### 2. Поиск
1. Пользователь формирует запрос и фильтры.
2. В зависимости от режима выполняется keyword, semantic или hybrid поиск.
3. При необходимости применяется rerank.
4. Выдача показывает не только результат, но и explain-блок с причинами попадания в выдачу.
5. Для авторизованных пользователей поисковая история может использоваться для рекомендаций.

### 3. Коллекции
- пользователь может создавать свои коллекции;
- коллекции имеют визуальное превью на основе верхних публикаций;
- на странице коллекции можно делиться ссылкой;
- реакции сведены к компактной цветной итоговой оценке.

### 4. CMS-ветка
- объявления и редакторские страницы живут в Wagtail;
- структура дерева предзаполняется через `bootstrap_wagtail`;
- CMS-страницы доступны из публичной навигации сайта.

## Что уже можно расширять

### UI и темы
См. [docs/ui-extension-guide.md](docs/ui-extension-guide.md)

### CMS-структура
См. [docs/cms-guide.md](docs/cms-guide.md)

### Редакторские сценарии
См. [docs/content-editor-guide.md](docs/content-editor-guide.md)

## Роли и доступ

### Посетитель
- просмотр каталога и карточек изданий;
- поиск;
- просмотр объявлений и CMS-страниц;
- просмотр публичных коллекций.

### Авторизованный пользователь
- история поиска;
- рекомендации;
- свои коллекции.

### Редактор / администратор
- работа с черновиками и публикациями;
- загрузка файлов и превью;
- управление справочниками;
- Django admin;
- Wagtail CMS.

На текущем этапе редактирование изданий на сайте ограничено административными ролями (`is_staff`, `is_admin`, `is_superuser`).

## Ограничения текущего прототипа

- ручной upload превью поддерживается, но редакторские операции по изображениям пока минимальны;
- Wagtail admin пока не брендируется глубоко, чтобы не ломать базовый интерфейс CMS;
- для production потребуется донастроить storage, security, бэкапы и CI/CD;
- часть эксплуатационных сценариев описана документально, но не покрыта автотестами полностью.

## Карта документации

- [docs/architecture.md](docs/architecture.md) — архитектура и границы модулей
- [docs/development-workflows.md](docs/development-workflows.md) — локальная разработка и повседневные сценарии
- [docs/search-and-indexing.md](docs/search-and-indexing.md) — поиск, Milvus, индексация, benchmark
- [docs/ui-extension-guide.md](docs/ui-extension-guide.md) — темы, языки, UI-расширение
- [docs/cms-guide.md](docs/cms-guide.md) — Wagtail, базовая структура CMS и её развитие
- [docs/content-editor-guide.md](docs/content-editor-guide.md) — работа редактора с изданиями, черновиками, коллекциями и превью

## Автор

Проект выполнен **Maxim Merkurev**.

GitHub проекта: <https://github.com/Bit-Maximum/institutional-repository-prototype>
