from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0003_publicationchunk"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="file_extension",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="publication",
            name="has_extracted_text",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="publication",
            name="text_extraction_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="publication",
            name="text_extraction_status",
            field=models.CharField(
                choices=[
                    ("pending", "Ожидает анализа"),
                    ("fulltext", "Извлечён основной текст"),
                    ("metadata_only_unsupported", "Только метаданные: формат не поддерживается"),
                    ("metadata_only_nontext", "Только метаданные: нетекстовая структура"),
                    ("metadata_only_missing", "Только метаданные: файл отсутствует"),
                    ("metadata_only_error", "Только метаданные: ошибка извлечения"),
                ],
                default="pending",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="publicationchunk",
            name="source_kind",
            field=models.CharField(
                choices=[("fulltext", "Основной текст"), ("metadata", "Только метаданные")],
                default="fulltext",
                max_length=16,
            ),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["text_extraction_status"], name="idx_pubs_extract_status"),
        ),
    ]
