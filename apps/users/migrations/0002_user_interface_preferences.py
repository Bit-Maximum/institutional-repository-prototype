from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="preferred_language",
            field=models.CharField(default="ru", max_length=16, verbose_name="Предпочитаемый язык интерфейса"),
        ),
        migrations.AddField(
            model_name="user",
            name="preferred_theme_mode",
            field=models.CharField(
                choices=[
                    ("system", "Следовать настройкам устройства"),
                    ("light", "Светлая"),
                    ("dark", "Тёмная"),
                ],
                default="system",
                max_length=16,
                verbose_name="Предпочитаемая тема интерфейса",
            ),
        ),
    ]
