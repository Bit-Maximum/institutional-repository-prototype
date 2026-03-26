from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0005_publication_vector_index_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicationchunk",
            name="section_title",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="publicationchunk",
            name="index_quality",
            field=models.FloatField(default=1.0),
        ),
    ]
