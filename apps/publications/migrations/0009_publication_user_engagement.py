from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("publications", "0008_publication_workflow_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicationUserEngagement",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("download_count", models.PositiveIntegerField(default=0)),
                ("first_viewed_at", models.DateTimeField(blank=True, null=True)),
                ("last_viewed_at", models.DateTimeField(blank=True, null=True)),
                ("first_downloaded_at", models.DateTimeField(blank=True, null=True)),
                ("last_downloaded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_engagements", to="publications.publication")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="publication_engagements", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "publication_user_engagements",
                "verbose_name": "Взаимодействие пользователя с изданием",
                "verbose_name_plural": "Взаимодействия пользователей с изданиями",
            },
        ),
        migrations.AddConstraint(
            model_name="publicationuserengagement",
            constraint=models.UniqueConstraint(fields=("publication", "user"), name="uq_pub_user_engagement"),
        ),
        migrations.AddIndex(
            model_name="publicationuserengagement",
            index=models.Index(fields=["user", "last_viewed_at"], name="idx_pub_eng_user_view"),
        ),
        migrations.AddIndex(
            model_name="publicationuserengagement",
            index=models.Index(fields=["user", "last_downloaded_at"], name="idx_pub_eng_user_dl"),
        ),
        migrations.AddIndex(
            model_name="publicationuserengagement",
            index=models.Index(fields=["publication"], name="idx_pub_eng_pub"),
        ),
    ]
