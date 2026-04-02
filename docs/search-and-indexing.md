# Поиск, Milvus и индексация

## Режимы поиска

Проект поддерживает три режима:

### `keyword`
Традиционный поиск по полям PostgreSQL и связанным сущностям.

Подходит, когда:
- пользователь знает точное название;
- важны строгие фильтры;
- нужен контролируемый традиционный сценарий.

### `semantic`
Поиск по смысловой близости через Milvus и embeddings.

Подходит, когда:
- запрос сформулирован естественным языком;
- важнее смысл, а не точное совпадение терминов;
- требуется поиск по содержанию документа, а не только по метаданным.

### `hybrid`
Комбинация keyword и semantic retrieval.

Это основной режим по умолчанию для публичного интерфейса.

## Retrieval pipeline

1. Из текста публикации формируются chunk'и.
2. Chunk'и индексируются в Milvus.
3. Для semantic/hybrid режима строится набор кандидатов.
4. При включённом rerank лучшие кандидаты уточняются cross-encoder моделью.
5. На выходе выдаётся ранжированный список публикаций.

## Используемые модели

### Основная retrieval-модель
- `BAAI/bge-m3`

Используется для:
- dense retrieval;
- sparse retrieval;
- мультиязычной работы;
- длинного контекста.

### Reranker
- `BAAI/bge-reranker-v2-m3`

Используется как опциональный слой повышения точности.

## Профили поиска

### `SEARCH_PROFILE=fast`
Быстрый профиль:
- меньше кандидатов;
- rerank обычно отключён;
- лучше для dev и CPU-среды.

### `SEARCH_PROFILE=quality`
Более качественный, но дорогой профиль:
- больше кандидатов;
- чаще включён rerank;
- выше latency.

## Переменные окружения поиска

Наиболее важные:

```env
SEARCH_PROFILE=fast
SEARCH_PAGE_SIZE=10
SEARCH_CANDIDATE_POOL_SIZE=120
SEARCH_RERANK_ENABLED=False
SEARCH_RERANK_MODEL=BAAI/bge-reranker-v2-m3
SEARCH_RERANK_TOP_K=12
SEARCH_KEYWORD_MIN_SCORE=20
SEARCH_SEMANTIC_MIN_SCORE=0.2
SEARCH_HYBRID_MIN_SCORE=0.2
SEARCH_KEYWORD_RELATIVE_CUTOFF=0.0
SEARCH_SEMANTIC_RELATIVE_CUTOFF=0.35
SEARCH_HYBRID_RELATIVE_CUTOFF=0.4
```

## Warmup

```bash
uv run python manage.py warm_search_models
```

Нужен, чтобы:
- заранее скачать модели;
- сократить задержку первого semantic/hybrid запроса.

## Создание и проверка коллекции Milvus

```bash
uv run python manage.py ensure_milvus_collection
```

Это штатный способ убедиться, что коллекция существует и готова к работе.

## Переиндексация публикаций

### Базовая
```bash
uv run python manage.py reindex_publications
```

### Полная пересборка
```bash
uv run python manage.py reindex_publications --force
```

### С пересозданием коллекции
```bash
uv run python manage.py reindex_publications --recreate-collection
```

## Benchmark

```bash
uv run python manage.py benchmark_search
```

Дополнительно можно указывать:
- `--spec`
- `--runs`
- `--top-k`
- `--output-dir`

Benchmark нужен для:
- сравнения режимов поиска;
- анализа latency;
- оценки Hits@K, MRR и других метрик на контрольных запросах.

## Explain-блок в выдаче

На странице поиска у каждого результата может раскрываться блок с объяснением. Он показывает:
- итоговый score;
- raw score;
- основу совпадения;
- этап ранжирования;
- фрагмент, повлиявший на выдачу.

Этот блок intentionally вторичен и не должен мешать просмотру карточек.

## Превью и поиск

Превью напрямую не участвуют в retrieval, но сильно улучшают UX:
- в каталоге;
- в поиске;
- в коллекциях;
- на карточке издания.

При необходимости пересобираются отдельно:

```bash
uv run python manage.py generate_publication_previews --force
```
