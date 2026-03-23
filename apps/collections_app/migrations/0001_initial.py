from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("publications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Collection",
            fields=[
                ("id", models.BigAutoField(db_column="collection_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                (
                    "author_user",
                    models.ForeignKey(
                        db_column="author_user_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="collections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Коллекция изданий",
                "verbose_name_plural": "Коллекции изданий",
                "db_table": "publication_collections",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="CollectionPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("collection", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("collection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="collections_app.collection")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь коллекции и издания",
                "verbose_name_plural": "Связи коллекций и изданий",
                "db_table": "collection_publications",
            },
        ),
        migrations.AddField(
            model_name="collection",
            name="publications",
            field=models.ManyToManyField(blank=True, related_name="collections", through="collections_app.CollectionPublication", to="publications.publication"),
        ),
        migrations.AddIndex(
            model_name="collection",
            index=models.Index(fields=["author_user"], name="idx_pub_cols_author_id"),
        ),
        migrations.AddIndex(
            model_name="collectionpublication",
            index=models.Index(fields=["publication"], name="idx_col_pubs_pub_id"),
        ),
    ]
