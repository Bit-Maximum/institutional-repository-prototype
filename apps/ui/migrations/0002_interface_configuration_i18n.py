from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ui", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="interfaceconfiguration",
            name="public_site_tagline_translations",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Расширяемый словарь вида {'en': 'Semantic search, collections, and intelligent recommendations'}.",
                verbose_name="Локализованные варианты подзаголовка",
            ),
        ),
        migrations.AddField(
            model_name="interfaceconfiguration",
            name="public_site_title_translations",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Расширяемый словарь вида {'en': 'Institutional Repository'}. Если для выбранного языка записи нет, используется основное поле названия.",
                verbose_name="Локализованные варианты названия сайта",
            ),
        ),
    ]
