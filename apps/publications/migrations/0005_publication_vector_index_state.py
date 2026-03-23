from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0004_publication_extraction_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="vector_index_signature",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="publication",
            name="vector_indexed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["vector_index_signature"], name="idx_pubs_vector_sig"),
        ),
    ]
