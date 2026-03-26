from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("publications", "0007_publication_derived_characteristics"),
    ]

    operations = [
        migrations.AddField(
            model_name="publication",
            name="draft_revision",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="publication",
            name="last_saved_by",
            field=models.ForeignKey(blank=True, db_column="last_saved_by_user_id", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="saved_publications", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="publication",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="publication",
            name="published_by",
            field=models.ForeignKey(blank=True, db_column="published_by_user_id", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="published_publications", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="publication",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["last_saved_by"], name="idx_pubs_saved_by_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["published_by"], name="idx_pubs_published_by_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["is_draft", "updated_at"], name="idx_pubs_draft_updated"),
        ),
    ]
