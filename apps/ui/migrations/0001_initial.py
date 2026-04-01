from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InterfaceConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("singleton_key", models.PositiveSmallIntegerField(default=1, editable=False, unique=True)),
                (
                    "public_site_title",
                    models.CharField(default="Институциональный репозиторий", max_length=255, verbose_name="Название публичного сайта"),
                ),
                (
                    "public_site_tagline",
                    models.CharField(
                        blank=True,
                        default="Семантический поиск, коллекции и интеллектуальные рекомендации",
                        max_length=255,
                        verbose_name="Подзаголовок публичного сайта",
                    ),
                ),
                (
                    "active_style",
                    models.CharField(
                        default="academic",
                        help_text="Определяет базовый визуальный стиль всего публичного сайта. Новые стили можно добавлять через реестр apps.ui.registry.",
                        max_length=64,
                        verbose_name="Активный глобальный стиль",
                    ),
                ),
                (
                    "default_theme_mode",
                    models.CharField(
                        choices=[
                            ("system", "Следовать настройкам устройства"),
                            ("light", "Светлая"),
                            ("dark", "Тёмная"),
                        ],
                        default="system",
                        max_length=16,
                        verbose_name="Тема по умолчанию",
                    ),
                ),
                (
                    "default_language",
                    models.CharField(default="ru", max_length=16, verbose_name="Язык публичного интерфейса по умолчанию"),
                ),
                (
                    "allow_user_theme_mode_switch",
                    models.BooleanField(default=True, verbose_name="Разрешить пользователям переключать светлую/тёмную тему"),
                ),
                (
                    "allow_user_language_switch",
                    models.BooleanField(default=True, verbose_name="Разрешить пользователям переключать язык интерфейса"),
                ),
            ],
            options={
                "verbose_name": "Конфигурация публичного интерфейса",
                "verbose_name_plural": "Конфигурация публичного интерфейса",
            },
        ),
    ]
