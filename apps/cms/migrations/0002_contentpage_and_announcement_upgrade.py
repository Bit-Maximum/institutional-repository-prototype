import datetime
import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
from django.db import migrations, models


CONTENT_STREAM_BLOCKS = [
    (
        'heading',
        wagtail.blocks.CharBlock(form_classname='title', icon='title', label='Подзаголовок'),
    ),
    (
        'paragraph',
        wagtail.blocks.RichTextBlock(
            features=['bold', 'italic', 'link', 'ol', 'ul', 'hr', 'h3', 'h4'],
            label='Текстовый блок',
        ),
    ),
    (
        'callout',
        wagtail.blocks.StructBlock(
            [
                ('eyebrow', wagtail.blocks.CharBlock(required=False, label='Метка')),
                ('title', wagtail.blocks.CharBlock(label='Заголовок')),
                ('text', wagtail.blocks.TextBlock(label='Текст')),
            ],
            icon='placeholder',
            label='Выделенный блок',
        ),
    ),
    (
        'quote',
        wagtail.blocks.StructBlock(
            [
                ('text', wagtail.blocks.TextBlock(label='Цитата')),
                ('attribution', wagtail.blocks.CharBlock(required=False, label='Источник')),
            ],
            icon='openquote',
            label='Цитата',
        ),
    ),
    (
        'buttons',
        wagtail.blocks.ListBlock(
            wagtail.blocks.StructBlock(
                [
                    ('label', wagtail.blocks.CharBlock(label='Подпись кнопки')),
                    ('url', wagtail.blocks.URLBlock(label='Ссылка')),
                    (
                        'style',
                        wagtail.blocks.ChoiceBlock(
                            choices=[('primary', 'Основная'), ('secondary', 'Вторичная')],
                            default='primary',
                            label='Стиль',
                        ),
                    ),
                ],
                icon='link',
                label='Кнопка',
            ),
            icon='link',
            label='Ряд кнопок',
        ),
    ),
    (
        'cards',
        wagtail.blocks.ListBlock(
            wagtail.blocks.StructBlock(
                [
                    ('eyebrow', wagtail.blocks.CharBlock(required=False, label='Метка')),
                    ('title', wagtail.blocks.CharBlock(label='Заголовок')),
                    ('text', wagtail.blocks.TextBlock(required=False, label='Текст карточки')),
                ],
                icon='placeholder',
                label='Карточка',
            ),
            icon='list-ul',
            label='Сетка карточек',
        ),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('intro', models.TextField(blank=True)),
                ('body', wagtail.fields.StreamField(CONTENT_STREAM_BLOCKS, blank=True, use_json_field=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.AddField(
            model_name='announcementpage',
            name='summary',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='announcementpage',
            name='body',
            field=wagtail.fields.StreamField(CONTENT_STREAM_BLOCKS, blank=True, use_json_field=True),
        ),
    ]
