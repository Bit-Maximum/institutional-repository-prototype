from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("search", "0002_initial")]

    operations = [
        migrations.AddField(
            model_name="searchquery",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterModelOptions(
            name="searchquery",
            options={
                "verbose_name": "Поисковый запрос",
                "verbose_name_plural": "Поисковые запросы",
                "db_table": "search_queries",
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
