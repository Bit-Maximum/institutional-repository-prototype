from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicDegree",
            fields=[
                ("name", models.TextField(unique=True)),
                ("id", models.BigAutoField(db_column="academic_degree_id", primary_key=True, serialize=False)),
            ],
            options={
                "verbose_name": "Учёная степень",
                "verbose_name_plural": "Учёные степени",
                "db_table": "academic_degrees",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Bibliography",
            fields=[
                ("id", models.BigAutoField(db_column="bibliography_id", primary_key=True, serialize=False)),
                ("bibliographic_description", models.TextField()),
            ],
            options={
                "verbose_name": "Библиографическое описание",
                "verbose_name_plural": "Библиографические описания",
                "db_table": "bibliographies",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="GraphicEdition",
            fields=[
                ("id", models.BigAutoField(db_column="graphic_edition_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("document_link", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Графическое издание",
                "verbose_name_plural": "Графические издания",
                "db_table": "graphic_editions",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Keyword",
            fields=[
                ("name", models.TextField(unique=True)),
                ("id", models.BigAutoField(db_column="keyword_id", primary_key=True, serialize=False)),
            ],
            options={
                "verbose_name": "Ключевое слово",
                "verbose_name_plural": "Ключевые слова",
                "db_table": "keywords",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PublicationLanguage",
            fields=[
                ("name", models.TextField(unique=True)),
                ("id", models.BigAutoField(db_column="language_id", primary_key=True, serialize=False)),
            ],
            options={
                "verbose_name": "Язык издания",
                "verbose_name_plural": "Языки изданий",
                "db_table": "publication_languages",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PublicationPeriodicity",
            fields=[
                ("name", models.TextField(unique=True)),
                ("id", models.BigAutoField(db_column="periodicity_id", primary_key=True, serialize=False)),
            ],
            options={
                "verbose_name": "Периодичность издания",
                "verbose_name_plural": "Периодичности изданий",
                "db_table": "publication_periodicities",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PublicationType",
            fields=[
                ("name", models.TextField(unique=True)),
                ("id", models.BigAutoField(db_column="publication_type_id", primary_key=True, serialize=False)),
            ],
            options={
                "verbose_name": "Тип издания",
                "verbose_name_plural": "Типы изданий",
                "db_table": "publication_types",
                "ordering": ["name"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PublicationPlace",
            fields=[
                ("id", models.BigAutoField(db_column="place_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("address", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Место публикации",
                "verbose_name_plural": "Места публикации",
                "db_table": "publication_places",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Publisher",
            fields=[
                ("id", models.BigAutoField(db_column="publisher_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("address", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Издатель",
                "verbose_name_plural": "Издатели",
                "db_table": "publishers",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Copyright",
            fields=[
                ("id", models.BigAutoField(db_column="copyright_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                ("address", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Копирайт",
                "verbose_name_plural": "Копирайты",
                "db_table": "copyrights",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="PublicationSubtype",
            fields=[
                ("id", models.BigAutoField(db_column="publication_subtype_id", primary_key=True, serialize=False)),
                ("name", models.TextField()),
                (
                    "publication_type",
                    models.ForeignKey(
                        db_column="publication_type_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subtypes",
                        to="publications.publicationtype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Подтип издания",
                "verbose_name_plural": "Подтипы изданий",
                "db_table": "publication_subtypes",
                "ordering": ["publication_type__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="Author",
            fields=[
                ("id", models.BigAutoField(db_column="author_id", primary_key=True, serialize=False)),
                ("full_name", models.TextField()),
                ("position", models.TextField(blank=True)),
                ("author_mark", models.TextField(blank=True)),
                (
                    "academic_degree",
                    models.ForeignKey(
                        blank=True,
                        db_column="academic_degree_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="authors",
                        to="publications.academicdegree",
                    ),
                ),
            ],
            options={
                "verbose_name": "Автор",
                "verbose_name_plural": "Авторы",
                "db_table": "authors",
                "ordering": ["full_name"],
            },
        ),
        migrations.CreateModel(
            name="ScientificSupervisor",
            fields=[
                ("id", models.BigAutoField(db_column="scientific_supervisor_id", primary_key=True, serialize=False)),
                ("full_name", models.TextField()),
                ("position", models.TextField(blank=True)),
                (
                    "academic_degree",
                    models.ForeignKey(
                        blank=True,
                        db_column="academic_degree_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scientific_supervisors",
                        to="publications.academicdegree",
                    ),
                ),
            ],
            options={
                "verbose_name": "Научный руководитель",
                "verbose_name_plural": "Научные руководители",
                "db_table": "scientific_supervisors",
                "ordering": ["full_name"],
            },
        ),
        migrations.CreateModel(
            name="Publication",
            fields=[
                ("id", models.BigAutoField(db_column="publication_id", primary_key=True, serialize=False)),
                ("title", models.TextField()),
                ("subject_code", models.IntegerField(blank=True, null=True)),
                ("start_page", models.IntegerField(blank=True, null=True)),
                ("end_page", models.IntegerField(blank=True, null=True)),
                ("file", models.FileField(blank=True, db_column="main_text_link", null=True, upload_to="publications/")),
                ("publication_format_link", models.TextField(blank=True)),
                ("contents", models.TextField(blank=True)),
                ("grant_text", models.TextField(blank=True)),
                ("publication_year", models.IntegerField(blank=True, null=True)),
                ("uploaded_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("volume_number", models.PositiveIntegerField(blank=True, null=True)),
                ("issue_number", models.PositiveIntegerField(blank=True, null=True)),
                ("grif_text", models.TextField(blank=True)),
                ("is_draft", models.BooleanField(default=False)),
                (
                    "language",
                    models.ForeignKey(
                        blank=True,
                        db_column="language_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="publications",
                        to="publications.publicationlanguage",
                    ),
                ),
                (
                    "periodicity",
                    models.ForeignKey(
                        blank=True,
                        db_column="periodicity_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="publications",
                        to="publications.publicationperiodicity",
                    ),
                ),
                (
                    "publication_subtype",
                    models.ForeignKey(
                        blank=True,
                        db_column="publication_subtype_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="publications",
                        to="publications.publicationsubtype",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        db_column="uploaded_by_user_id",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="uploaded_publications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Издание",
                "verbose_name_plural": "Издания",
                "db_table": "publications",
                "ordering": ["-uploaded_at"],
            },
        ),
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                ("pk", models.CompositePrimaryKey("user", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommended_to", to="publications.publication")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Рекомендация",
                "verbose_name_plural": "Рекомендации",
                "db_table": "recommendations",
            },
        ),
        migrations.CreateModel(
            name="PublicationPlacePublication",
            fields=[
                ("pk", models.CompositePrimaryKey("place", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("place", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publicationplace")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь места публикации и издания",
                "verbose_name_plural": "Связи мест публикации и изданий",
                "db_table": "publication_place_publications",
            },
        ),
        migrations.CreateModel(
            name="PublisherPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("publisher", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
                ("publisher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publisher")),
            ],
            options={
                "verbose_name": "Связь издателя и издания",
                "verbose_name_plural": "Связи издателей и изданий",
                "db_table": "publisher_publications",
            },
        ),
        migrations.CreateModel(
            name="CopyrightPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("copyright", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("copyright", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.copyright")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь копирайта и издания",
                "verbose_name_plural": "Связи копирайтов и изданий",
                "db_table": "copyright_publications",
            },
        ),
        migrations.CreateModel(
            name="CopyrightPublisher",
            fields=[
                ("pk", models.CompositePrimaryKey("copyright", "publisher", blank=True, editable=False, primary_key=True, serialize=False)),
                ("copyright", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.copyright")),
                ("publisher", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publisher")),
            ],
            options={
                "verbose_name": "Связь копирайта и издателя",
                "verbose_name_plural": "Связи копирайтов и издателей",
                "db_table": "copyright_publishers",
            },
        ),
        migrations.CreateModel(
            name="AuthorPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("author", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.author")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь автора и издания",
                "verbose_name_plural": "Связи авторов и изданий",
                "db_table": "author_publications",
            },
        ),
        migrations.CreateModel(
            name="CopyrightAuthor",
            fields=[
                ("pk", models.CompositePrimaryKey("copyright", "author", blank=True, editable=False, primary_key=True, serialize=False)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.author")),
                ("copyright", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.copyright")),
            ],
            options={
                "verbose_name": "Связь копирайта и автора",
                "verbose_name_plural": "Связи копирайтов и авторов",
                "db_table": "copyright_authors",
            },
        ),
        migrations.CreateModel(
            name="BibliographyPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("bibliography", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("bibliography", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.bibliography")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь библиографии и издания",
                "verbose_name_plural": "Связи библиографий и изданий",
                "db_table": "bibliography_publications",
            },
        ),
        migrations.CreateModel(
            name="GraphicEditionPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("graphic_edition", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("graphic_edition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.graphicedition")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь графического издания и публикации",
                "verbose_name_plural": "Связи графических изданий и публикаций",
                "db_table": "graphic_edition_publications",
            },
        ),
        migrations.CreateModel(
            name="KeywordPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("keyword", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("keyword", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.keyword")),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
            ],
            options={
                "verbose_name": "Связь ключевого слова и издания",
                "verbose_name_plural": "Связи ключевых слов и изданий",
                "db_table": "keyword_publications",
            },
        ),
        migrations.CreateModel(
            name="ScientificSupervisorPublication",
            fields=[
                ("pk", models.CompositePrimaryKey("scientific_supervisor", "publication", blank=True, editable=False, primary_key=True, serialize=False)),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.publication")),
                ("scientific_supervisor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="publications.scientificsupervisor")),
            ],
            options={
                "verbose_name": "Связь научного руководителя и издания",
                "verbose_name_plural": "Связи научных руководителей и изданий",
                "db_table": "scientific_supervisor_publications",
            },
        ),
        migrations.AddField(
            model_name="copyright",
            name="authors",
            field=models.ManyToManyField(blank=True, related_name="copyrights", through="publications.CopyrightAuthor", to="publications.author"),
        ),
        migrations.AddField(
            model_name="copyright",
            name="publishers",
            field=models.ManyToManyField(blank=True, related_name="copyrights", through="publications.CopyrightPublisher", to="publications.publisher"),
        ),
        migrations.AddField(
            model_name="publication",
            name="authors",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.AuthorPublication", to="publications.author"),
        ),
        migrations.AddField(
            model_name="publication",
            name="bibliographies",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.BibliographyPublication", to="publications.bibliography"),
        ),
        migrations.AddField(
            model_name="publication",
            name="copyrights",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.CopyrightPublication", to="publications.copyright"),
        ),
        migrations.AddField(
            model_name="publication",
            name="graphic_editions",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.GraphicEditionPublication", to="publications.graphicedition"),
        ),
        migrations.AddField(
            model_name="publication",
            name="keywords",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.KeywordPublication", to="publications.keyword"),
        ),
        migrations.AddField(
            model_name="publication",
            name="publication_places",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.PublicationPlacePublication", to="publications.publicationplace"),
        ),
        migrations.AddField(
            model_name="publication",
            name="publishers",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.PublisherPublication", to="publications.publisher"),
        ),
        migrations.AddField(
            model_name="publication",
            name="scientific_supervisors",
            field=models.ManyToManyField(blank=True, related_name="publications", through="publications.ScientificSupervisorPublication", to="publications.scientificsupervisor"),
        ),
        migrations.AddIndex(
            model_name="publicationsubtype",
            index=models.Index(fields=["publication_type"], name="idx_pub_subtypes_type_id"),
        ),
        migrations.AddConstraint(
            model_name="publicationsubtype",
            constraint=models.UniqueConstraint(fields=("name", "publication_type"), name="uq_pub_subtypes_name_type"),
        ),
        migrations.AddIndex(
            model_name="author",
            index=models.Index(fields=["academic_degree"], name="idx_authors_academic_degree_id"),
        ),
        migrations.AddIndex(
            model_name="scientificsupervisor",
            index=models.Index(fields=["academic_degree"], name="idx_sci_sup_degree_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["uploaded_by"], name="idx_pubs_uploaded_by_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["publication_subtype"], name="idx_pubs_subtype_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["periodicity"], name="idx_pubs_period_id"),
        ),
        migrations.AddIndex(
            model_name="publication",
            index=models.Index(fields=["language"], name="idx_publications_language_id"),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["publication"], name="idx_recom_pub_id"),
        ),
        migrations.AddIndex(
            model_name="publicationplacepublication",
            index=models.Index(fields=["publication"], name="idx_place_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="publisherpublication",
            index=models.Index(fields=["publication"], name="idx_publisher_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="copyrightpublication",
            index=models.Index(fields=["publication"], name="idx_cpr_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="copyrightpublisher",
            index=models.Index(fields=["publisher"], name="idx_cpr_pubs_publisher_id"),
        ),
        migrations.AddIndex(
            model_name="authorpublication",
            index=models.Index(fields=["publication"], name="idx_author_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="copyrightauthor",
            index=models.Index(fields=["author"], name="idx_cpr_auth_author_id"),
        ),
        migrations.AddIndex(
            model_name="bibliographypublication",
            index=models.Index(fields=["publication"], name="idx_biblio_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="graphiceditionpublication",
            index=models.Index(fields=["publication"], name="idx_graph_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="keywordpublication",
            index=models.Index(fields=["publication"], name="idx_kw_pubs_pub_id"),
        ),
        migrations.AddIndex(
            model_name="scientificsupervisorpublication",
            index=models.Index(fields=["publication"], name="idx_sup_pubs_pub_id"),
        ),
        migrations.AddConstraint(
            model_name="publication",
            constraint=models.CheckConstraint(condition=Q(start_page__isnull=True) | Q(end_page__isnull=True) | Q(start_page__lte=F("end_page")), name="chk_publications_pages"),
        ),
        migrations.AddConstraint(
            model_name="publication",
            constraint=models.CheckConstraint(condition=Q(publication_year__isnull=True) | Q(publication_year__gte=0, publication_year__lte=9999), name="chk_publications_year"),
        ),
        migrations.AddConstraint(
            model_name="publication",
            constraint=models.CheckConstraint(condition=Q(volume_number__isnull=True) | Q(volume_number__gte=0), name="chk_publications_volume"),
        ),
        migrations.AddConstraint(
            model_name="publication",
            constraint=models.CheckConstraint(condition=Q(issue_number__isnull=True) | Q(issue_number__gte=0), name="chk_publications_issue"),
        ),
    ]
