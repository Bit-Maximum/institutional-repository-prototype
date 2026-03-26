from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("collections_app", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name="collection",
            name="description",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="collection",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name="collectionpublication",
            name="added_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.CreateModel(
            name="CollectionReaction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("value", models.SmallIntegerField(choices=[(1, "Лайк"), (-1, "Дизлайк")])),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("collection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactions", to="collections_app.collection")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="collection_reactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "collection_reactions",
                "verbose_name": "Оценка коллекции",
                "verbose_name_plural": "Оценки коллекций",
            },
        ),
        migrations.AddConstraint(
            model_name="collectionreaction",
            constraint=models.UniqueConstraint(fields=("collection", "user"), name="uq_collection_reactions_user"),
        ),
        migrations.AddConstraint(
            model_name="collectionreaction",
            constraint=models.CheckConstraint(condition=models.Q(("value__in", [-1, 1])), name="chk_collection_reaction_value"),
        ),
        migrations.AddIndex(
            model_name="collectionreaction",
            index=models.Index(fields=["collection", "value"], name="idx_col_react_value"),
        ),
        migrations.AddIndex(
            model_name="collectionreaction",
            index=models.Index(fields=["user"], name="idx_col_react_user"),
        ),
    ]
