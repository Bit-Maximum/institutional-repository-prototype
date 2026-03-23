-- PostgreSQL 14+ only. Этот скрипт не предназначен для SQLite.
BEGIN;

-- Моковые данные для сквозного тестирования прототипа институционального репозитория.
-- Скрипт рассчитан на PostgreSQL и может применяться повторно:
-- для справочников и связей используются ON CONFLICT / WHERE NOT EXISTS.
--
-- Тестовые учётные записи:
--   admin@example.com    / AdminPass123!
--   editor@example.com   / EditorPass123!
--   reader@example.com   / ReaderPass123!
--   student@example.com  / StudentPass123!

/* -------------------------------
 * Пользователи
 * ------------------------------- */
INSERT INTO users (
    email,
    password_hash,
    full_name,
    is_admin,
    is_staff,
    is_active,
    is_superuser,
    last_login
)
VALUES
    (
        'admin@example.com',
        'pbkdf2_sha256$600000$adminsalt123$1gyYxfiD5Zbt/re/AwDf9UOuLcNUu+4G++RGw4Wlh5o=',
        'Администратор репозитория',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        NULL
    ),
    (
        'editor@example.com',
        'pbkdf2_sha256$600000$editorsalt123$VTf+oyAvydx0tD+NezwjI+Pr1AL4n59dHKo5si6KKVY=',
        'Редактор контента',
        TRUE,
        TRUE,
        TRUE,
        FALSE,
        NULL
    ),
    (
        'reader@example.com',
        'pbkdf2_sha256$600000$readersalt123$P3ZXZe84WcmJSEmlDVdWuymhcd5RwvvMQB5RpMs8FfA=',
        'Научный сотрудник',
        FALSE,
        FALSE,
        TRUE,
        FALSE,
        NULL
    ),
    (
        'student@example.com',
        'pbkdf2_sha256$600000$studentsalt123$6+pLha/p9YEB6JBl5L0NdJVopk9pENkR1KKt26uGFw4=',
        'Студент магистратуры',
        FALSE,
        FALSE,
        TRUE,
        FALSE,
        NULL
    )
ON CONFLICT (email) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    full_name = EXCLUDED.full_name,
    is_admin = EXCLUDED.is_admin,
    is_staff = EXCLUDED.is_staff,
    is_active = EXCLUDED.is_active,
    is_superuser = EXCLUDED.is_superuser;

/* -------------------------------
 * Справочники
 * ------------------------------- */
INSERT INTO academic_degrees (name)
VALUES
    ('без степени'),
    ('кандидат технических наук'),
    ('доктор технических наук'),
    ('кандидат физико-математических наук'),
    ('доктор педагогических наук')
ON CONFLICT (name) DO NOTHING;

INSERT INTO publication_periodicities (name)
VALUES
    ('разово'),
    ('ежегодно'),
    ('ежеквартально'),
    ('ежемесячно'),
    ('семестрово')
ON CONFLICT (name) DO NOTHING;

INSERT INTO publication_languages (name)
VALUES
    ('русский'),
    ('английский'),
    ('китайский')
ON CONFLICT (name) DO NOTHING;

INSERT INTO publication_types (name)
VALUES
    ('Научное издание'),
    ('Учебное издание'),
    ('Справочно-энциклопедическое издание'),
    ('Художественное издание')
ON CONFLICT (name) DO NOTHING;

INSERT INTO publication_subtypes (name, publication_type_id)
SELECT v.name, pt.publication_type_id
FROM (
    VALUES
        ('Научная статья', 'Научное издание'),
        ('Монография', 'Научное издание'),
        ('Сборник материалов конференции', 'Научное издание'),
        ('Учебное пособие', 'Учебное издание'),
        ('Методические указания', 'Учебное издание'),
        ('Электронный курс лекций', 'Учебное издание'),
        ('Словарь', 'Справочно-энциклопедическое издание'),
        ('Справочник', 'Справочно-энциклопедическое издание'),
        ('Альманах', 'Художественное издание')
) AS v(name, type_name)
JOIN publication_types pt ON pt.name = v.type_name
ON CONFLICT ON CONSTRAINT uq_publication_subtypes_name_type DO NOTHING;

INSERT INTO keywords (name)
VALUES
    ('семантический поиск'),
    ('гибридный поиск'),
    ('институциональный репозиторий'),
    ('векторные базы данных'),
    ('milvus'),
    ('splade'),
    ('django'),
    ('wagtail'),
    ('программная инженерия'),
    ('машинное обучение'),
    ('анализ данных'),
    ('цифровые библиотеки'),
    ('библиографическое описание'),
    ('учебные материалы'),
    ('словарь терминов')
ON CONFLICT (name) DO NOTHING;

INSERT INTO publication_places (name, address)
SELECT x.name, x.address
FROM (
    VALUES
        ('Владивосток', 'Россия, г. Владивосток, о. Русский, кампус ДВФУ'),
        ('Москва', 'Россия, г. Москва'),
        ('Санкт-Петербург', 'Россия, г. Санкт-Петербург'),
        ('Новосибирск', 'Россия, г. Новосибирск'),
        ('Казань', 'Россия, г. Казань')
) AS x(name, address)
WHERE NOT EXISTS (
    SELECT 1 FROM publication_places pp
    WHERE pp.name = x.name AND COALESCE(pp.address, '') = COALESCE(x.address, '')
);

INSERT INTO publishers (name, address)
SELECT x.name, x.address
FROM (
    VALUES
        ('ДВФУ', 'Россия, Владивосток, о. Русский, кампус ДВФУ'),
        ('Издательство Наука', 'Россия, Москва'),
        ('Springer Nature', 'Heidelberg, Germany'),
        ('Университетское издательство', 'Россия, Санкт-Петербург'),
        ('Центр цифровых библиотек', 'Россия, Новосибирск')
) AS x(name, address)
WHERE NOT EXISTS (
    SELECT 1 FROM publishers p2
    WHERE p2.name = x.name AND COALESCE(p2.address, '') = COALESCE(x.address, '')
);

INSERT INTO graphic_editions (name, document_link)
SELECT x.name, x.document_link
FROM (
    VALUES
        ('Схема архитектуры модульного монолита', '/media/mock/diagrams/architecture-module-monolith.pdf'),
        ('Диаграмма последовательности индексирования', '/media/mock/diagrams/indexing-sequence.pdf'),
        ('Инфологическая модель репозитория', '/media/mock/diagrams/infological-model.pdf'),
        ('ER-диаграмма физической схемы БД', '/media/mock/diagrams/er-schema.pdf')
) AS x(name, document_link)
WHERE NOT EXISTS (
    SELECT 1 FROM graphic_editions ge
    WHERE ge.name = x.name
);

INSERT INTO bibliographies (bibliographic_description)
SELECT x.bibliographic_description
FROM (
    VALUES
        ('Fedotov A., Baidavletov A., Zhizhimov O. Цифровой репозиторий в научно-образовательной информационной системе. Вестник НГУ. Серия: Информационные технологии. 2015. №3.'),
        ('Mackenzie J., Zhuang S., Zuccon G. Exploring the Representation Power of SPLADE Models. arXiv. 2023.'),
        ('Gao L., Callan J. Unsupervised Corpus Aware Language Model Pre-training for Dense Passage Retrieval. arXiv. 2021.'),
        ('Wang J., Yin X., Gao R. Milvus: A Purpose-Built Vector Data Management System. ACM. 2021.'),
        ('ГОСТ Р 7.0.100-2018. Библиографическая запись. Библиографическое описание. Общие требования и правила составления.'),
        ('Django Documentation. The web framework for perfectionists with deadlines.'),
        ('Wagtail Documentation. Django CMS focused on flexibility and editorial experience.')
) AS x(bibliographic_description)
WHERE NOT EXISTS (
    SELECT 1 FROM bibliographies b
    WHERE b.bibliographic_description = x.bibliographic_description
);

INSERT INTO authors (full_name, academic_degree_id, position, author_mark)
SELECT
    x.full_name,
    ad.academic_degree_id,
    x.position,
    x.author_mark
FROM (
    VALUES
        ('Меркурьев Максим Алексеевич', 'без степени', 'магистрант', 'основной автор'),
        ('Иванов Сергей Петрович', 'кандидат технических наук', 'доцент', 'научный редактор'),
        ('Петрова Анна Викторовна', 'доктор технических наук', 'профессор', 'ответственный редактор'),
        ('Соколова Мария Дмитриевна', 'кандидат физико-математических наук', 'старший научный сотрудник', 'автор'),
        ('Ким Алексей Олегович', 'без степени', 'разработчик', 'составитель'),
        ('Смирнова Елена Игоревна', 'доктор педагогических наук', 'профессор', 'автор учебного курса'),
        ('Орлов Павел Николаевич', 'кандидат технических наук', 'заведующий лабораторией', 'автор'),
        ('Ли Юн', 'кандидат технических наук', 'исследователь', 'соавтор')
) AS x(full_name, degree_name, position, author_mark)
LEFT JOIN academic_degrees ad ON ad.name = x.degree_name
WHERE NOT EXISTS (
    SELECT 1 FROM authors a
    WHERE a.full_name = x.full_name AND COALESCE(a.position, '') = COALESCE(x.position, '')
);

INSERT INTO scientific_supervisors (full_name, academic_degree_id, position)
SELECT
    x.full_name,
    ad.academic_degree_id,
    x.position
FROM (
    VALUES
        ('Федотов Александр Михайлович', 'доктор технических наук', 'профессор'),
        ('Байдавлетов Арман Талгатович', 'кандидат технических наук', 'доцент'),
        ('Самбетбаева Марина Алексеевна', 'доктор педагогических наук', 'профессор')
) AS x(full_name, degree_name, position)
LEFT JOIN academic_degrees ad ON ad.name = x.degree_name
WHERE NOT EXISTS (
    SELECT 1 FROM scientific_supervisors s
    WHERE s.full_name = x.full_name AND COALESCE(s.position, '') = COALESCE(x.position, '')
);

INSERT INTO copyrights (name, address)
SELECT x.name, x.address
FROM (
    VALUES
        ('© Дальневосточный федеральный университет, 2026', 'Россия, Владивосток, о. Русский, кампус ДВФУ'),
        ('© Авторский коллектив лаборатории цифровых библиотек, 2025', 'Россия, Москва'),
        ('© Университетское издательство, 2024', 'Россия, Санкт-Петербург'),
        ('© Центр цифровых библиотек, 2026', 'Россия, Новосибирск')
) AS x(name, address)
WHERE NOT EXISTS (
    SELECT 1 FROM copyrights c
    WHERE c.name = x.name
);

/* -------------------------------
 * Публикации
 * ------------------------------- */
INSERT INTO publications (
    title,
    subject_code,
    start_page,
    end_page,
    main_text_link,
    publication_format_link,
    contents,
    grant_text,
    uploaded_by_user_id,
    publication_year,
    uploaded_at,
    volume_number,
    issue_number,
    publication_subtype_id,
    periodicity_id,
    grif_text,
    language_id,
    is_draft
)
SELECT
    x.title,
    x.subject_code,
    x.start_page,
    x.end_page,
    x.main_text_link,
    x.publication_format_link,
    x.contents,
    x.grant_text,
    u.user_id,
    x.publication_year,
    x.uploaded_at,
    x.volume_number,
    x.issue_number,
    ps.publication_subtype_id,
    pp.periodicity_id,
    x.grif_text,
    pl.language_id,
    x.is_draft
FROM (
    VALUES
        (
            'Архитектура институционального репозитория с гибридным поиском',
            101,
            1,
            24,
            'mock/publications/repository-architecture-hybrid-search.pdf',
            'PDF',
            $$В публикации рассматривается архитектура институционального репозитория, построенного как модульный монолит. Особое внимание уделяется гибридному поиску, который сочетает традиционный поиск по метаданным и семантическое ранжирование по содержимому текста. Описываются роли Django, PostgreSQL, Milvus и Wagtail в составе единой программной системы.$$,
            'Исследование выполнено в рамках университетского проекта по цифровым библиотекам.',
            'editor@example.com',
            2026,
            TIMESTAMP '2026-03-01 10:00:00',
            NULL,
            NULL,
            'Монография',
            'разово',
            'Рекомендовано к использованию в исследовательских проектах.',
            'русский',
            FALSE
        ),
        (
            'Применение SPLADE и Milvus для семантического поиска научных публикаций',
            102,
            25,
            42,
            'mock/publications/splade-milvus-semantic-search.pdf',
            'PDF',
            $$Статья посвящена применению sparse-эмбеддингов SPLADE и векторной базы данных Milvus для поиска публикаций по смысловой близости. Анализируется извлечение текстовых признаков из статей и влияние гибридного поиска на полноту выдачи.$$,
            'Подготовлено при поддержке лаборатории интеллектуального анализа текстов.',
            'reader@example.com',
            2025,
            TIMESTAMP '2025-12-15 15:30:00',
            12,
            4,
            'Научная статья',
            'ежеквартально',
            'Одобрено редакционной коллегией.',
            'русский',
            FALSE
        ),
        (
            'Методические рекомендации по курсу Программная инженерия',
            201,
            1,
            68,
            'mock/publications/software-engineering-guidelines.pdf',
            'PDF',
            $$Методические указания содержат требования к выполнению лабораторных работ, примеры UML-диаграмм, рекомендации по проектированию веб-систем и правила оформления отчётов. Материал рассчитан на бакалавров и магистрантов.$$,
            'Учебное издание подготовлено для направления 09.04.04.',
            'editor@example.com',
            2025,
            TIMESTAMP '2025-09-01 09:00:00',
            NULL,
            NULL,
            'Методические указания',
            'семестрово',
            'Допущено учебно-методическим советом.',
            'русский',
            FALSE
        ),
        (
            'Учебное пособие по анализу данных на Python',
            202,
            1,
            180,
            'mock/publications/python-data-analysis-tutorial.pdf',
            'PDF',
            $$Пособие охватывает основы обработки таблиц, визуализации данных, статистического анализа и подготовки датасетов для машинного обучения. Отдельный раздел посвящён работе с текстовыми коллекциями и подготовке документов к индексированию.$$,
            'Подготовлено в рамках обновления образовательной программы.',
            'editor@example.com',
            2024,
            TIMESTAMP '2024-11-20 11:45:00',
            NULL,
            NULL,
            'Учебное пособие',
            'разово',
            'Рекомендовано для самостоятельной работы студентов.',
            'русский',
            FALSE
        ),
        (
            'Толковый словарь терминов машинного обучения',
            301,
            1,
            95,
            'mock/publications/ml-glossary.pdf',
            'PDF',
            $$Словарь содержит определения терминов, связанных с машинным обучением, векторизацией текстов, ранжированием, индексированием и оценкой качества поиска. Пособие удобно использовать как справочник для студентов и исследователей.$$,
            'Справочное издание для образовательных и научных проектов.',
            'reader@example.com',
            2026,
            TIMESTAMP '2026-01-18 14:20:00',
            NULL,
            NULL,
            'Словарь',
            'разово',
            'Согласовано с терминологической комиссией.',
            'русский',
            FALSE
        ),
        (
            'Справочник по оформлению библиографических описаний',
            302,
            1,
            54,
            'mock/publications/bibliography-style-guide.pdf',
            'PDF',
            $$Справочник описывает правила подготовки библиографических описаний для электронных изданий, статей, монографий, сборников конференций и цифровых ресурсов. Материал основан на действующих стандартах и примерах из университетской практики.$$,
            'Подготовлено редакционно-издательским отделом.',
            'editor@example.com',
            2025,
            TIMESTAMP '2025-05-10 12:00:00',
            NULL,
            NULL,
            'Справочник',
            'разово',
            'Утверждено для использования в издательском цикле.',
            'русский',
            FALSE
        ),
        (
            'Сборник трудов конференции по цифровым библиотекам и репозиториям',
            103,
            1,
            220,
            'mock/publications/digital-libraries-conference-proceedings.pdf',
            'PDF',
            $$В сборнике представлены доклады по цифровым библиотекам, интеллектуальному поиску, метаданным Dublin Core, извлечению текста из PDF и DOCX, а также интеграции векторных баз данных в университетские репозитории.$$,
            'Материалы международной научно-практической конференции.',
            'admin@example.com',
            2025,
            TIMESTAMP '2025-10-12 16:40:00',
            3,
            1,
            'Сборник материалов конференции',
            'ежегодно',
            'Публикуется по решению программного комитета конференции.',
            'русский',
            FALSE
        ),
        (
            'Электронный курс лекций по цифровым библиотекам',
            203,
            1,
            132,
            'mock/publications/digital-libraries-lecture-course.pdf',
            'PDF',
            $$Курс лекций раскрывает принципы организации цифровых библиотек, управление метаданными, пользовательские сценарии поиска, архитектуру каталогов и основы семантического поиска по текстовым коллекциям.$$,
            'Подготовлено для магистерской программы по программной инженерии.',
            'editor@example.com',
            2026,
            TIMESTAMP '2026-02-05 08:30:00',
            NULL,
            NULL,
            'Электронный курс лекций',
            'семестрово',
            'Одобрено кафедрой.',
            'русский',
            FALSE
        ),
        (
            'Литературный альманах университетского кампуса',
            401,
            1,
            76,
            'mock/publications/campus-literary-almanac.pdf',
            'PDF',
            $$Альманах объединяет художественные тексты студентов и преподавателей. Запись добавлена в прототип для демонстрации того, что репозиторий способен работать не только с научными, но и с художественными электронными изданиями.$$,
            'Проект студенческого издательского клуба.',
            'student@example.com',
            2024,
            TIMESTAMP '2024-04-14 18:10:00',
            NULL,
            NULL,
            'Альманах',
            'ежегодно',
            'Внутривузовское издание.',
            'русский',
            FALSE
        ),
        (
            'Черновик каталога электронных изданий кафедры',
            204,
            1,
            12,
            'mock/publications/draft-department-catalog.pdf',
            'PDF',
            $$Черновая запись предназначена для проверки сценариев редактирования, повторной загрузки текста и скрытия ещё не опубликованных материалов из пользовательской выдачи.$$,
            'Служебный документ для внутренней проверки.',
            'editor@example.com',
            2026,
            TIMESTAMP '2026-03-12 09:15:00',
            NULL,
            NULL,
            'Методические указания',
            'разово',
            'Не публиковать до завершения проверки.',
            'русский',
            TRUE
        )
) AS x(
    title,
    subject_code,
    start_page,
    end_page,
    main_text_link,
    publication_format_link,
    contents,
    grant_text,
    uploader_email,
    publication_year,
    uploaded_at,
    volume_number,
    issue_number,
    subtype_name,
    periodicity_name,
    grif_text,
    language_name,
    is_draft
)
JOIN users u ON u.email = x.uploader_email
LEFT JOIN publication_subtypes ps ON ps.name = x.subtype_name
LEFT JOIN publication_periodicities pp ON pp.name = x.periodicity_name
LEFT JOIN publication_languages pl ON pl.name = x.language_name
WHERE NOT EXISTS (
    SELECT 1 FROM publications p WHERE p.title = x.title
);

/* -------------------------------
 * Связи: авторы, ключевые слова, издатели и т.д.
 * ------------------------------- */
INSERT INTO author_publications (author_id, publication_id)
SELECT a.author_id, p.publication_id
FROM (
    VALUES
        ('Меркурьев Максим Алексеевич', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Иванов Сергей Петрович', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Соколова Мария Дмитриевна', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Ли Юн', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Смирнова Елена Игоревна', 'Методические рекомендации по курсу Программная инженерия'),
        ('Смирнова Елена Игоревна', 'Учебное пособие по анализу данных на Python'),
        ('Иванов Сергей Петрович', 'Справочник по оформлению библиографических описаний'),
        ('Петрова Анна Викторовна', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('Орлов Павел Николаевич', 'Электронный курс лекций по цифровым библиотекам'),
        ('Ким Алексей Олегович', 'Толковый словарь терминов машинного обучения'),
        ('Ким Алексей Олегович', 'Черновик каталога электронных изданий кафедры'),
        ('Меркурьев Максим Алексеевич', 'Литературный альманах университетского кампуса')
) AS x(author_name, publication_title)
JOIN authors a ON a.full_name = x.author_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO scientific_supervisor_publications (scientific_supervisor_id, publication_id)
SELECT s.scientific_supervisor_id, p.publication_id
FROM (
    VALUES
        ('Федотов Александр Михайлович', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Байдавлетов Арман Талгатович', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Самбетбаева Марина Алексеевна', 'Методические рекомендации по курсу Программная инженерия'),
        ('Самбетбаева Марина Алексеевна', 'Электронный курс лекций по цифровым библиотекам')
) AS x(supervisor_name, publication_title)
JOIN scientific_supervisors s ON s.full_name = x.supervisor_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO keyword_publications (keyword_id, publication_id)
SELECT k.keyword_id, p.publication_id
FROM (
    VALUES
        ('семантический поиск', 'Архитектура институционального репозитория с гибридным поиском'),
        ('гибридный поиск', 'Архитектура институционального репозитория с гибридным поиском'),
        ('институциональный репозиторий', 'Архитектура институционального репозитория с гибридным поиском'),
        ('splade', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('milvus', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('векторные базы данных', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('django', 'Архитектура институционального репозитория с гибридным поиском'),
        ('wagtail', 'Архитектура институционального репозитория с гибридным поиском'),
        ('программная инженерия', 'Методические рекомендации по курсу Программная инженерия'),
        ('учебные материалы', 'Методические рекомендации по курсу Программная инженерия'),
        ('анализ данных', 'Учебное пособие по анализу данных на Python'),
        ('машинное обучение', 'Учебное пособие по анализу данных на Python'),
        ('словарь терминов', 'Толковый словарь терминов машинного обучения'),
        ('машинное обучение', 'Толковый словарь терминов машинного обучения'),
        ('библиографическое описание', 'Справочник по оформлению библиографических описаний'),
        ('цифровые библиотеки', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('институциональный репозиторий', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('цифровые библиотеки', 'Электронный курс лекций по цифровым библиотекам'),
        ('учебные материалы', 'Электронный курс лекций по цифровым библиотекам'),
        ('институциональный репозиторий', 'Черновик каталога электронных изданий кафедры')
) AS x(keyword_name, publication_title)
JOIN keywords k ON k.name = x.keyword_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO publication_place_publications (place_id, publication_id)
SELECT pp.place_id, p.publication_id
FROM (
    VALUES
        ('Владивосток', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Москва', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Владивосток', 'Методические рекомендации по курсу Программная инженерия'),
        ('Санкт-Петербург', 'Учебное пособие по анализу данных на Python'),
        ('Москва', 'Толковый словарь терминов машинного обучения'),
        ('Владивосток', 'Справочник по оформлению библиографических описаний'),
        ('Новосибирск', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('Владивосток', 'Электронный курс лекций по цифровым библиотекам'),
        ('Владивосток', 'Литературный альманах университетского кампуса'),
        ('Владивосток', 'Черновик каталога электронных изданий кафедры')
) AS x(place_name, publication_title)
JOIN publication_places pp ON pp.name = x.place_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO publisher_publications (publisher_id, publication_id)
SELECT pb.publisher_id, p.publication_id
FROM (
    VALUES
        ('ДВФУ', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Springer Nature', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('ДВФУ', 'Методические рекомендации по курсу Программная инженерия'),
        ('Университетское издательство', 'Учебное пособие по анализу данных на Python'),
        ('Центр цифровых библиотек', 'Толковый словарь терминов машинного обучения'),
        ('ДВФУ', 'Справочник по оформлению библиографических описаний'),
        ('Центр цифровых библиотек', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('ДВФУ', 'Электронный курс лекций по цифровым библиотекам'),
        ('Университетское издательство', 'Литературный альманах университетского кампуса'),
        ('ДВФУ', 'Черновик каталога электронных изданий кафедры')
) AS x(publisher_name, publication_title)
JOIN publishers pb ON pb.name = x.publisher_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO copyright_publications (copyright_id, publication_id)
SELECT c.copyright_id, p.publication_id
FROM (
    VALUES
        ('© Дальневосточный федеральный университет, 2026', 'Архитектура институционального репозитория с гибридным поиском'),
        ('© Авторский коллектив лаборатории цифровых библиотек, 2025', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('© Дальневосточный федеральный университет, 2026', 'Методические рекомендации по курсу Программная инженерия'),
        ('© Университетское издательство, 2024', 'Учебное пособие по анализу данных на Python'),
        ('© Центр цифровых библиотек, 2026', 'Толковый словарь терминов машинного обучения'),
        ('© Дальневосточный федеральный университет, 2026', 'Справочник по оформлению библиографических описаний'),
        ('© Центр цифровых библиотек, 2026', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('© Дальневосточный федеральный университет, 2026', 'Электронный курс лекций по цифровым библиотекам'),
        ('© Университетское издательство, 2024', 'Литературный альманах университетского кампуса'),
        ('© Дальневосточный федеральный университет, 2026', 'Черновик каталога электронных изданий кафедры')
) AS x(copyright_name, publication_title)
JOIN copyrights c ON c.name = x.copyright_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO copyright_authors (copyright_id, author_id)
SELECT c.copyright_id, a.author_id
FROM (
    VALUES
        ('© Дальневосточный федеральный университет, 2026', 'Меркурьев Максим Алексеевич'),
        ('© Дальневосточный федеральный университет, 2026', 'Иванов Сергей Петрович'),
        ('© Авторский коллектив лаборатории цифровых библиотек, 2025', 'Соколова Мария Дмитриевна'),
        ('© Авторский коллектив лаборатории цифровых библиотек, 2025', 'Ли Юн'),
        ('© Университетское издательство, 2024', 'Смирнова Елена Игоревна'),
        ('© Центр цифровых библиотек, 2026', 'Ким Алексей Олегович')
) AS x(copyright_name, author_name)
JOIN copyrights c ON c.name = x.copyright_name
JOIN authors a ON a.full_name = x.author_name
ON CONFLICT DO NOTHING;

INSERT INTO copyright_publishers (copyright_id, publisher_id)
SELECT c.copyright_id, p.publisher_id
FROM (
    VALUES
        ('© Дальневосточный федеральный университет, 2026', 'ДВФУ'),
        ('© Авторский коллектив лаборатории цифровых библиотек, 2025', 'Springer Nature'),
        ('© Университетское издательство, 2024', 'Университетское издательство'),
        ('© Центр цифровых библиотек, 2026', 'Центр цифровых библиотек')
) AS x(copyright_name, publisher_name)
JOIN copyrights c ON c.name = x.copyright_name
JOIN publishers p ON p.name = x.publisher_name
ON CONFLICT DO NOTHING;

INSERT INTO bibliography_publications (bibliography_id, publication_id)
SELECT b.bibliography_id, p.publication_id
FROM (
    VALUES
        ('Fedotov A., Baidavletov A., Zhizhimov O. Цифровой репозиторий в научно-образовательной информационной системе. Вестник НГУ. Серия: Информационные технологии. 2015. №3.', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Mackenzie J., Zhuang S., Zuccon G. Exploring the Representation Power of SPLADE Models. arXiv. 2023.', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Gao L., Callan J. Unsupervised Corpus Aware Language Model Pre-training for Dense Passage Retrieval. arXiv. 2021.', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Wang J., Yin X., Gao R. Milvus: A Purpose-Built Vector Data Management System. ACM. 2021.', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Django Documentation. The web framework for perfectionists with deadlines.', 'Методические рекомендации по курсу Программная инженерия'),
        ('ГОСТ Р 7.0.100-2018. Библиографическая запись. Библиографическое описание. Общие требования и правила составления.', 'Справочник по оформлению библиографических описаний'),
        ('Wagtail Documentation. Django CMS focused on flexibility and editorial experience.', 'Электронный курс лекций по цифровым библиотекам')
) AS x(description, publication_title)
JOIN bibliographies b ON b.bibliographic_description = x.description
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO graphic_edition_publications (graphic_edition_id, publication_id)
SELECT ge.graphic_edition_id, p.publication_id
FROM (
    VALUES
        ('Схема архитектуры модульного монолита', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Диаграмма последовательности индексирования', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Инфологическая модель репозитория', 'Электронный курс лекций по цифровым библиотекам'),
        ('ER-диаграмма физической схемы БД', 'Сборник трудов конференции по цифровым библиотекам и репозиториям')
) AS x(graphic_name, publication_title)
JOIN graphic_editions ge ON ge.name = x.graphic_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

/* -------------------------------
 * Коллекции, запросы и рекомендации
 * ------------------------------- */
INSERT INTO publication_collections (name, author_user_id)
SELECT x.name, u.user_id
FROM (
    VALUES
        ('Семантический поиск и Milvus', 'reader@example.com'),
        ('Учебные материалы по программной инженерии', 'student@example.com'),
        ('Цифровые библиотеки и репозитории', 'reader@example.com'),
        ('Материалы редактора', 'editor@example.com')
) AS x(name, user_email)
JOIN users u ON u.email = x.user_email
WHERE NOT EXISTS (
    SELECT 1 FROM publication_collections pc
    WHERE pc.name = x.name AND pc.author_user_id = u.user_id
);

INSERT INTO collection_publications (collection_id, publication_id)
SELECT c.collection_id, p.publication_id
FROM (
    VALUES
        ('Семантический поиск и Milvus', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('Семантический поиск и Milvus', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Учебные материалы по программной инженерии', 'Методические рекомендации по курсу Программная инженерия'),
        ('Учебные материалы по программной инженерии', 'Учебное пособие по анализу данных на Python'),
        ('Учебные материалы по программной инженерии', 'Электронный курс лекций по цифровым библиотекам'),
        ('Цифровые библиотеки и репозитории', 'Сборник трудов конференции по цифровым библиотекам и репозиториям'),
        ('Цифровые библиотеки и репозитории', 'Архитектура институционального репозитория с гибридным поиском'),
        ('Материалы редактора', 'Справочник по оформлению библиографических описаний'),
        ('Материалы редактора', 'Черновик каталога электронных изданий кафедры')
) AS x(collection_name, publication_title)
JOIN publication_collections c ON c.name = x.collection_name
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

INSERT INTO search_queries (query_text, query_topic, filters, user_id)
SELECT x.query_text, x.query_topic, x.filters, u.user_id
FROM (
    VALUES
        ('семантический поиск в репозитории', 1, '{"mode": "hybrid", "language": "русский"}', 'reader@example.com'),
        ('учебное пособие python анализ данных', 2, '{"mode": "keyword", "type": "Учебное издание"}', 'student@example.com'),
        ('оформление библиографического описания электронных ресурсов', 3, '{"mode": "semantic"}', 'editor@example.com'),
        ('milvus splade sparse retrieval', 4, '{"mode": "semantic", "language": "английский"}', 'reader@example.com'),
        ('цифровые библиотеки и dublin core', 5, '{"mode": "hybrid"}', 'student@example.com'),
        ('черновик каталога кафедры', 6, '{"mode": "keyword", "include_drafts": true}', 'editor@example.com')
) AS x(query_text, query_topic, filters, user_email)
JOIN users u ON u.email = x.user_email
WHERE NOT EXISTS (
    SELECT 1 FROM search_queries sq
    WHERE sq.query_text = x.query_text AND sq.user_id = u.user_id
);

INSERT INTO recommendations (user_id, publication_id)
SELECT u.user_id, p.publication_id
FROM (
    VALUES
        ('reader@example.com', 'Архитектура институционального репозитория с гибридным поиском'),
        ('reader@example.com', 'Применение SPLADE и Milvus для семантического поиска научных публикаций'),
        ('student@example.com', 'Учебное пособие по анализу данных на Python'),
        ('student@example.com', 'Электронный курс лекций по цифровым библиотекам'),
        ('editor@example.com', 'Справочник по оформлению библиографических описаний'),
        ('editor@example.com', 'Методические рекомендации по курсу Программная инженерия')
) AS x(user_email, publication_title)
JOIN users u ON u.email = x.user_email
JOIN publications p ON p.title = x.publication_title
ON CONFLICT DO NOTHING;

COMMIT;
