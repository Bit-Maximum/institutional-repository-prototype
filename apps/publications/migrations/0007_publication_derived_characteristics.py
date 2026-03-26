from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0006_publicationchunk_context_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="derived_characteristics",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
