# Institutional Repository Prototype

Стартовый каркас модульного монолита для прототипа институционального репозитория.

## Что уже заложено

- Django как основа веб-приложения и административной панели.
- Wagtail как CMS-слой для публикации объявлений и информационных страниц.
- PostgreSQL как основное хранилище предметных сущностей.
- Milvus как векторное хранилище для семантического поиска.
- Извлечение текста из PDF и DOCX.
- Три режима поиска: keyword, semantic, hybrid.
- Пользовательские коллекции изданий.

## Структура

```text
apps/
  core/           базовые страницы и общие примеси
  users/          регистрация и пользовательские сценарии
  publications/   издания, авторы, типы изданий
  collections_app/ пользовательские коллекции
  ingestion/      извлечение текста и подготовка документа к индексации
  search/         keyword / semantic / hybrid поиск
  vector_store/   изоляция работы с Milvus
  cms/            Wagtail-модели страниц
```

## Быстрый старт

### 1. Поднять PostgreSQL

```bash
docker compose up -d
```

### 2. Подготовить окружение

```bash
cp .env.example .env
uv sync
```

### 3. Применить миграции и инициализировать сервисы

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py bootstrap_wagtail
uv run python manage.py ensure_milvus_collection
uv run python manage.py createsuperuser
```

### 4. Запустить сервер

```bash
uv run python manage.py runserver
```

## Маршруты

- `/` — главная страница
- `/publications/` — каталог изданий
- `/search/` — поиск
- `/collections/` — коллекции
- `/accounts/register/` — регистрация
- `/admin/` — Django admin
- `/cms-admin/` — Wagtail admin
- `/pages/` — публичные страницы Wagtail

## Milvus в дев-режиме

По умолчанию `MILVUS_URI=./var/milvus/milvus.db`. Это позволяет использовать Milvus Lite локально без отдельного контейнера.

Если понадобится отдельный сервер Milvus, можно заменить `MILVUS_URI` на `http://localhost:19530` и поднять standalone-конфигурацию по официальной инструкции Milvus.

## Что делать дальше

1. Зафиксировать сгенерированные миграции доменных приложений в репозитории.
2. Привязать загрузку файлов к полноценному workflow черновика публикации.
3. Расширить модель метаданных под конкретные виды изданий из диссертации.
4. Добавить тестовый корпус документов и замерить качество поиска.
