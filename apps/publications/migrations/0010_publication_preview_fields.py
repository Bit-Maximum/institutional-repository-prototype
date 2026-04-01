from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("publications", "0009_publication_user_engagement"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="preview_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="publication",
            name="preview_image",
            field=models.ImageField(blank=True, null=True, upload_to="publication_previews/"),
        ),
        migrations.AddField(
            model_name="publication",
            name="preview_kind",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Нет превью"),
                    ("pdf_first_page", "Первая страница PDF"),
                    ("uploaded_image", "Загруженное изображение"),
                    ("generated_placeholder", "Сгенерированная обложка"),
                ],
                default="",
                max_length=32,
            ),
        ),
    ]
