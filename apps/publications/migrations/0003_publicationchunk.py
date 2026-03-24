from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicationChunk",
            fields=[
                ("id", models.BigAutoField(db_column="publication_chunk_id", primary_key=True, serialize=False)),
                ("chunk_index", models.PositiveIntegerField()),
                ("text", models.TextField()),
                ("page_start", models.PositiveIntegerField(blank=True, null=True)),
                ("page_end", models.PositiveIntegerField(blank=True, null=True)),
                ("char_count", models.PositiveIntegerField(default=0)),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                (
                    "publication",
                    models.ForeignKey(
                        db_column="publication_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chunks",
                        to="publications.publication",
                    ),
                ),
            ],
            options={
                "db_table": "publication_chunks",
                "verbose_name": "Фрагмент издания",
                "verbose_name_plural": "Фрагменты изданий",
                "ordering": ["publication_id", "chunk_index"],
            },
        ),
        migrations.AddConstraint(
            model_name="publicationchunk",
            constraint=models.UniqueConstraint(fields=("publication", "chunk_index"), name="uq_pub_chunks_pub_idx"),
        ),
        migrations.AddConstraint(
            model_name="publicationchunk",
            constraint=models.CheckConstraint(
                condition=models.Q(("page_start__isnull", True), ("page_end__isnull", True), _connector="OR") | models.Q(("page_start__lte", models.F("page_end"))),
                name="chk_pub_chunks_pages",
            ),
        ),
        migrations.AddIndex(
            model_name="publicationchunk",
            index=models.Index(fields=["publication"], name="idx_pub_chunks_pub_id"),
        ),
    ]
