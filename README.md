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

## Инфраструктура в Docker

В Docker Compose поднимаются только инфраструктурные сервисы для разработки:

- PostgreSQL на `localhost:5432`
- Milvus Standalone на `localhost:19530`
- Milvus WebUI / health endpoint на `localhost:9091`

Само Django-приложение на данном этапе запускается локально через `uv`, без контейнеризации.

## Быстрый старт

### 1. Поднять инфраструктуру

```bash
docker compose up -d
```

Milvus будет поднят вместе со своими зависимостями `etcd` и `minio`.

`ensure_milvus_collection` только создаёт коллекцию и теперь не требует загрузки модели SPLADE.
Для команд, которые реально строят embeddings (`reindex_publications`, семантический поиск, индексация при загрузке), PyTorch всё ещё нужен в окружении проекта.

### 2. Подготовить окружение

```bash
cp .env.example .env
uv sync
```

Если окружение уже было создано ранее и в нём успела установиться несовместимая ветка `transformers`, просто повторно выполни `uv sync`, чтобы зафиксировать совместимую версию из `pyproject.toml`. В проект также добавлен `hf_xet`, чтобы модели Hugging Face на Xet Storage скачивались без дополнительных предупреждений.

### 3. Применить миграции и инициализировать сервисы

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py bootstrap_wagtail
uv run python manage.py ensure_milvus_collection
uv run python manage.py createsuperuser
```

### 4. Запустить сервер приложения

```bash
uv run python manage.py runserver
```


## Важное замечание по актуализации схемы

Доменные модели приведены в соответствие с эталонной физической схемой БД: добавлены словари, связи многие-ко-многим через отдельные таблицы и пользовательская модель `users.User`, соответствующая таблице `users`. Из-за смены `AUTH_USER_MODEL` и структуры доменных таблиц безопаснее всего работать с **чистой базой данных** и выполнить миграции заново.

Если у тебя уже есть локальная БД от старой версии каркаса, её лучше удалить и пересоздать перед `makemigrations` / `migrate`.

## Маршруты

- `/` — главная страница
- `/publications/` — каталог изданий
- `/search/` — поиск
- `/collections/` — коллекции
- `/accounts/register/` — регистрация
- `/admin/` — Django admin
- `/cms-admin/` — Wagtail admin
- `/pages/` — публичные страницы Wagtail

## Переменные окружения для локальной разработки

По умолчанию приложение подключается к сервисам, опубликованным Docker Compose на localhost:

```env
DATABASE_URL=postgresql://repository:repository@localhost:5432/repository
MILVUS_URI=http://localhost:19530
SEARCH_PAGE_SIZE=10
SEARCH_CANDIDATE_POOL_SIZE=200
```

`SEARCH_PAGE_SIZE` управляет размером страниц в каталоге и поиске.
`SEARCH_CANDIDATE_POOL_SIZE` определяет, сколько кандидатов заранее запрашивается для гибридного и семантического поиска, чтобы пагинация по этим режимам работала предсказуемо.

Такой режим удобен для активной разработки: инфраструктура работает в Docker, а Django остаётся запущенным локально.

Если позже приложение тоже будет перенесено в Docker Compose, эти значения нужно будет заменить на имена сервисов внутри compose-сети, например `db` и `milvus`.

## Что делать дальше

1. Зафиксировать сгенерированные миграции доменных приложений в репозитории.
2. Привязать загрузку файлов к полноценному workflow черновика публикации.
3. Расширить модель метаданных под конкретные виды изданий из диссертации.
4. Добавить тестовый корпус документов и замерить качество поиска.


## Подключение к базе данных

Проект автоматически загружает переменные из файла `.env` в корне репозитория.
По умолчанию используется PostgreSQL по адресу `postgresql://repository:repository@localhost:5432/repository`.
SQLite теперь используется только при явном указании `DATABASE_URL=sqlite:///db.sqlite3`.


## Обновлённый семантический поиск

- Индексация идёт по фрагментам (`publication_chunks`), а не по одному вектору на документ.
- По умолчанию используется `BAAI/bge-m3`: модель поддерживает dense+sparse retrieval, мультиязычность и длинный контекст.
- Для повышения точности поверх retrieval включён cross-encoder rerank на `BAAI/bge-reranker-v2-m3`.
- Для keyword / semantic / hybrid режимов добавлены настраиваемые пороги score, чтобы не показывать заведомо слабые результаты.
- После обновления настроек рекомендуется использовать новое имя коллекции Milvus (`publications_chunks_hybrid_v1`) или удалить старую sparse-коллекцию.
- После миграции БД нужно выполнить `uv run python manage.py migrate`, затем `uv sync`, `uv run python manage.py ensure_milvus_collection` и `uv run python manage.py reindex_publications`.

### Новые настройки поиска

```env
SEARCH_KEYWORD_MIN_SCORE=20
SEARCH_SEMANTIC_MIN_SCORE=0.2
SEARCH_HYBRID_MIN_SCORE=0.2
SEARCH_RERANK_ENABLED=True
SEARCH_RERANK_MODEL=BAAI/bge-reranker-v2-m3
SEARCH_RERANK_TOP_K=40
SEARCH_RERANK_MAX_TEXT_CHARS=2400
```

Практический смысл этих параметров:
- `SEARCH_KEYWORD_MIN_SCORE` — минимальный допустимый score в традиционном поиске.
- `SEARCH_SEMANTIC_MIN_SCORE` — минимальный score после rerank для semantic режима.
- `SEARCH_HYBRID_MIN_SCORE` — минимальный score после rerank для semantic-head гибридного режима.
- `SEARCH_RERANK_TOP_K` — сколько лучших кандидатов отправлять на cross-encoder rerank.
- `SEARCH_RERANK_MAX_TEXT_CHARS` — сколько текста фрагмента брать в reranker.

## Профили поиска

По умолчанию используется быстрый профиль `SEARCH_PROFILE=fast`: rerank отключён, пул кандидатов уменьшен, чтобы semantic/hybrid поиск оставался интерактивным на CPU.

Если нужно сравнить качество с более тяжёлым режимом, можно переключиться на `SEARCH_PROFILE=quality` или вручную включить rerank через `SEARCH_RERANK_ENABLED=True`.

Для прогрева моделей после установки зависимостей можно выполнить:

```bash
uv run python manage.py warm_search_models
```

Это позволит скачать и загрузить модели заранее, а не на первом пользовательском запросе.



## Поисковый warmup и относительный отсев

По умолчанию при старте `runserver` включён `SEARCH_WARMUP_ON_STARTUP=True`: сервис заранее загружает embedding-модель и подключает коллекцию Milvus, чтобы первый semantic/hybrid запрос не ждал инициализацию. Лог `Fetching 30 files` относится к скачиванию файлов модели с Hugging Face, а не к загрузке всех документов корпуса в память Django-процесса.

Для дополнительного отсечения слабых результатов можно задать относительные пороги:

```env
SEARCH_KEYWORD_RELATIVE_CUTOFF=0.0
SEARCH_SEMANTIC_RELATIVE_CUTOFF=0.35
SEARCH_HYBRID_RELATIVE_CUTOFF=0.4
```

Значение трактуется как доля от score лучшего результата в выдаче. Например, `0.5` означает: показывать только материалы с score не ниже 50% от лучшего совпадения.


## Benchmark-режим поиска

В проект добавлена management-команда для повторяемого замера качества и скорости поиска по контрольному набору запросов. Она умеет прогревать Milvus/модели, запускать кейсы во всех режимах поиска и сохранять JSON/CSV-отчёты.

Базовый запуск:

```bash
uv run python manage.py benchmark_search
```

По умолчанию команда читает спецификацию `benchmarks/search_benchmark.sample.json`. В ней можно задавать:
- `query` — текст запроса;
- `modes` — список режимов (`keyword`, `semantic`, `hybrid`);
- `filters` — дополнительные фильтры;
- `expected_publication_ids` или `expected_title_contains` — ожидаемые релевантные издания для расчёта Hits@K и MRR.

Пример с явной спецификацией и сохранением отчётов в отдельный каталог:

```bash
uv run python manage.py benchmark_search --spec benchmarks/search_benchmark.sample.json --runs 5 --top-k 5 --output-dir var/search_benchmarks
```

В JSON/CSV-отчётах сохраняются: latency (mean / median / p95), среднее число результатов, средний top score и, если для кейсов заданы ожидаемые документы, качества поиска по MRR, Hits@1/3/5, Precision@K и Recall@K.


## Faster bulk indexing

The `reindex_publications` command now supports a faster bulk pipeline:

```bash
uv run python manage.py reindex_publications
uv run python manage.py reindex_publications --recreate-collection
uv run python manage.py reindex_publications --force
```

What changed:
- chunk/vector state is tracked by `vector_index_signature` and `vector_indexed_at` on publications;
- unchanged publications are skipped automatically on repeated runs;
- when the Milvus collection is recreated, existing stored chunks are reused without parsing files again;
- chunk embeddings are generated in batches instead of one publication at a time;
- vector upserts/deletes are also batched.

Useful settings:
- `MILVUS_BGE_M3_BATCH_SIZE`
- `MILVUS_BGE_M3_DEVICE`
- `MILVUS_BGE_M3_USE_FP16`
- `MILVUS_UPSERT_BATCH_SIZE`
- `VECTOR_INDEX_MAX_EMBED_TEXTS`
- `VECTOR_REINDEX_PUBLICATION_BATCH_SIZE`
- `VECTOR_INDEX_SCHEMA_VERSION`

If you later change chunking/index-time logic in a way that should invalidate previous vectors, bump `VECTOR_INDEX_SCHEMA_VERSION` in `.env` and run `reindex_publications` again.


## CUDA по умолчанию

Проект теперь закрепляет `torch` на индекс PyTorch CUDA 12.6 через `uv`, а BGE-M3 по умолчанию использует `MILVUS_BGE_M3_DEVICE=auto`. Это означает: на машинах с доступной CUDA поиск и индексация будут работать через GPU, а на CPU-only окружениях сервис безопасно откатится на `cpu`. Конфигурация `uv` сделана через `[[tool.uv.index]]` и `[tool.uv.sources]`, что соответствует официальной документации uv для PyTorch индексов.


Дополнительно можно включить прогрев не только модели и коллекции, но и первого запроса:

- `SEARCH_WARMUP_RUN_QUERY=True`
- `SEARCH_WARMUP_SAMPLE_QUERY=поиск`

Это уменьшает задержку первого semantic/hybrid запроса после перезапуска сервера.


## Healthcheck endpoints

- `GET /health/live/` — liveness probe
- `GET /health/ready/` — readiness probe with database, vector store and startup warmup status
- `GET /health/` — alias of readiness probe

When startup warmup is enabled, the application logs a final readiness message after the search stack finishes loading and the service becomes ready to accept requests.
