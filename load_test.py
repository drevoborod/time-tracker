#!/usr/bin/env python3
import random
import core



DESCRIPTIONS = ["""Литературное сообщество 1920-х годов встретило появление романа весьма сдержанно. К числу тех, кто
поддержал соавторов, относились писатель Юрий Олеша, политический деятель Николай Бухарин, критик Анатолий Тарасенков
и некоторые другие современники Ильфа и Петрова. В 1949—1956 годах «Двенадцать стульев» — наряду с написанным позже
«Золотым телёнком» — были на основании постановления секретариата ЦК ВКП(б) запрещены к печати. Произведение было
неоднократно экранизировано.""",
                """Гай Лелий (лат. Gaius Laelius; умер после 160 года до н. э.) — древнеримский военачальник и
политический деятель из плебейского рода Лелиев, ближайший друг и сподвижник Публия Корнелия Сципиона
Африканского, сыгравший важную роль во Второй Пунической войне, консул 190 года до н. э.""",
                """В 2011 году среднемесячная зарплата в Норвегии составила 38 100 крон, что в среднем на 3,8 % больше,
чем в 2010 году. В среднем, мужчины зарабатывали на 6 тысяч крон больше, чем женщины — 40 800 и 34 800 крон
соответственно. Доля женской зарплаты за год выросла с 85 % до 85,3 %. В государственном секторе разрыв в
зарплатах женщин и мужчин практически не изменился и прирост произошёл в основном за счёт частного сектора""",
                """Король в губернии представлен губернатором (no:fylkesmann). Представительные органы губерний —
губернские собрания (no:fylkesting)""",
                """Га́ллий — элемент 13-й группы (по устаревшей классификации — главной подгруппы третьей группы)
четвёртого периода периодической системы химических элементов Д. И. Менделеева, с атомным номером 31. Обозначается
символом Ga (лат. Gallium). Относится к группе лёгких металлов. Простое вещество галлий (CAS-номер: 7440-55-3) —
мягкий хрупкий металл серебристо-белого (по другим данным светло-серого) цвета с синеватым оттенком.""",
                """Короткое описание 1""",
                """Short description 2""",
                """Not so short description 3""",
                """etc."""]

TASK_NAME = "task number"

TASK_SYMBOLS = []
for i in range(256, 1100):
    if 'а' <= chr(i) <= 'я' or 'А' <= chr(i) <= 'Я':
        TASK_SYMBOLS.append(chr(i))
for i in range(32, 128):
    TASK_SYMBOLS.append(chr(i))

TASKS_NUMBER = 2000
TASK_NAME_LEN = 25
TAGS = ['tag %d' % x for x in range(1, 21)]
DATES = ['11.02.2016', '19.09.1978', '01.06.2010', '14.11.2005', '04.08.2011', '02.02.2015']

core.check_database()

# Инициализируем работу с БД:
db = core.Db()

# Добавляем теги в БД:
for tag in TAGS:
    db.insert(table='tags', fields=('name', 'id'), values=(tag, None))

# Добавляем задачи в БД:
for n in range(1, int(TASKS_NUMBER / 2)):
    db.insert_task('%s %d' % (TASK_NAME, n))
print('\nInserting of first portion of tasks completed.')


# Добавляем ещё кучку задач с произвольными именами в БД:
for n in range(int(TASKS_NUMBER / 2)):
    task_name = []
    # Делаем имена произвольной длины:
    for i in range(random.randint(4, TASK_NAME_LEN)):
        task_name.append(random.choice(TASK_SYMBOLS))
    db.insert_task(r''.join(task_name))
print('\nInserting of second portion of tasks completed.\n')


# набор id тегов:
tag_ids = [x[1] for x in db.find_all('tags')]

# Добавить к каждой таске кучку привязанных дат и тегов, а также задать время и описание:
for task_id in [x[0] for x in db.find_all('tasks')]:
    for x in range(random.randint(1, len(tag_ids))):
        db.insert(table='tasks_tags', fields=('tag_id', 'task_id'), values=(random.choice(tag_ids), task_id))
    for x in range(random.randint(1, len(DATES))):
        db.insert(table='activity', fields=('date', 'task_id', 'spent_time'), values=(random.choice(DATES), task_id,
                                                                                   random.randint(0, 86000)))
    db.update(task_id, "description", random.choice(DESCRIPTIONS))
    db.update(task_id, "creation_date", random.choice(DATES))
    print('Task %d updated' % task_id)
print('\nTasks parametrization completed.\n')

db.cur.close()
db.con.close()

