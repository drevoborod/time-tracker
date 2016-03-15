#!/usr/bin/env python3

import sqlite3
import os
import time
import datetime

class DbErrors(Exception): pass

class Db():
    def __init__(self):
        self.db_filename = table_file
        if not os.path.exists(self.db_filename):
            self.create_table()
        self.con = sqlite3.connect(self.db_filename)
        self.cur = self.con.cursor()

    def create_table(self):
        with sqlite3.connect(self.db_filename) as con:
            con.executescript(table_structure)
            con.commit()

    def exec_script(self, script):
        """Выполняет произвольный скрипт. Возвращает всегда значение lastrowid."""
        try:
            if type(script) is not tuple:
                self.cur.execute(script)
            else:      # На случай, если вместо простого скрипта передан скрипт + значения для подстановки.
                self.cur.execute(script[0], script[1])
        except sqlite3.DatabaseError as err:
            raise DbErrors(err)
        else:
            self.con.commit()
            return self.cur.lastrowid

    def find_by_clause(self, table, field, value, searchfield):
        """Поиск в поле searchfield по условию field=value. """
        self.exec_script('select {3} from {0} where {1}="{2}"'.format(table, field, value, searchfield))
        return self.cur.fetchall()

    def find_all(self, table, sortfield=None):
        if not sortfield:
            self.exec_script('select * from {0}'.format(table))
        else:
            self.exec_script('select * from {0} order by {1} asc'.format(table, sortfield))
        return self.cur.fetchall()

    def insert(self, table, fields, values):
        """Добавление записи. Fields и values должны быть кортежами по 2 записи."""
        return self.exec_script(('insert into {0} {1} values (?, ?)'.format(table, fields), values))

    def insert_task(self, name):
        """Добавление задачи и соотвествующей записи в таблицы dates и tags."""
        date = date_format(datetime.datetime.now())     # Текущая дата в формате "ДД.ММ.ГГГГ".
        try:    # Пытаемся создать запись.
            rowid = self.exec_script(('insert into tasks (id, timer, task_name, creation_date) values (null, 0, ?, ?)', (name, date)))
        except sqlite3.IntegrityError:   # Если задача с таким именем уже есть, то возбуждаем исключение.
            raise DbErrors("Task name already exists")
        else:
            id = self.find_by_clause("tasks", "rowid", rowid, "id")[0][0]
            self.insert("dates", ("date", "task_id"), (date, id))
            self.insert("tags", ("tag_id", "task_id"), (1, id))
            return id      # Возвращаем id записи в таблице tasks, которую добавили.

    def update(self, id, field="timer", value=0, table="tasks", updfiled="id"):
        self.exec_script(("update {0} set {1}=? where {3}='{2}'".format(table, field, id, updfiled), (value, )))

    def update_task(self, id, field="timer", value=0):
        """Обновить запись в таблице задач. Если для этой задачи нет записи на текущую дату, добавляем такую запись."""
        date = date_format(datetime.datetime.now())
        if date not in [x[0] for x in self.find_by_clause(table="dates", field="task_id", value=id, searchfield="date")]:
            self.insert("dates", ("date", "task_id"), (date, id))
        self.update(id, field=field, value=value)

    def delete(self, ids, field="id", table="tasks"):
        """Удаляет несколько записей, поэтому ids должен быть кортежом."""
        # ToDo: Попробовать сделать нормальную подстановку в скрипт, без необходимости проверки длины ids.
        if len(ids) == 1:
            i = "('%s')" % ids[0]
        else:
            i = ids
        self.exec_script("delete from {1} where {2} in {0}".format(i, table, field))

    def delete_tasks(self, ids):
        """Удаление задач."""
        self.delete(ids)
        self.delete(ids, field="task_id", table="dates")
        self.delete(ids, field="task_id", table="timestamps")

    def tags_dict(self, taskid):
        """Создание списка тегов, их имён и значений для задачи с taskid."""
        tagnames = self.find_all("tagnames", sortfield="tag_name")     # [(tagname, 1), (tagname, 2)]
        self.exec_script('select t1.tag_id from tags as t1 join tagnames as t2 on t1.tag_id = t2.tag_id where t1.task_id=%d' % taskid)
        actual_tags = [x[0] for x in self.cur.fetchall()]    # [1, 3, ...]
        states_list = []   #  {1: [1, 'tag1'],  2: [0, 'tag2'], 3: [1, 'tag3']} - словарь актуальных состояний для тегов для данной таски.
        for k in tagnames:
            states_list.append([k[1], [1 if k[1] in actual_tags else 0, k[0]]])
        return states_list

    def simple_tagslist(self):
        """Возвращает список тегов в таков же формате, как tags_dict, но не привязанных к какой-то задаче."""
        tagslist = self.find_all("tagnames", sortfield="tag_name")
        res = [[y, [0, x]] for x, y in tagslist]
        res.reverse()
        return res

    def timestamps(self, taskid, current_time):
        """Возвращает список таймстемпов в таков же формате, как tags_dict."""
        timestamps = self.find_by_clause('timestamps', 'task_id', taskid, 'timestamp')
        res = [[x[0], [0, '{0}; {1} have passed since that moment'.format(time_format(x[0]), time_format(current_time - x[0]))]] for x in timestamps]
        res.reverse()
        return res

    def close(self):
        self.cur.close()
        self.con.close()


class Params:
    """Пустой класс, нужный для того, чтобы использовать в качестве хранилища переменных."""
    pass

def export(filename, text):
    expfile = open(filename, 'w')
    expfile.write(text)
    expfile.close()

def time_format(sec):
    """Функция возвращает время в удобочитаемом формате. Принимает секунды."""
    if sec < 86400:
        return time.strftime("%H:%M:%S", time.gmtime(sec))
    else:
        return time.strftime("%jd:%H:%M:%S", time.gmtime(sec))

def date_format(date):
    """Возвращает дату в формате ДД:ММ:ГГГГ. На вход принимает datetime."""
    return datetime.datetime.strftime(date, '%d.%m.%Y')


table_file = 'tasks.db'
table_structure = """\
                create table tasks (id integer primary key autoincrement,
                task_name text unique,
                timer int,
                description text,
                creation_date text);
                create table options (option_name text unique,
                value text);
                create table dates (date text,
                task_id int);
                create table tags (tag_id int,
                task_id int);
                create table timestamps (timestamp int,
                task_id int);
                create table tagnames (tag_name text unique,
                tag_id integer primary key autoincrement);
                insert into tagnames values ('default', 1);
                insert into options (option_name) values ('filter');
                insert into options (option_name, value) values ('filter_tags', '');
                insert into options (option_name, value) values ('filter_dates', '');
                """

help_text = """Приложение позволяет вести учёт потраченного на задачу времени. Чтобы выбрать задачу или создать новую, \
следует нажать кнопку "Task" на главном экране. В окне выбора задач реализована возможность редактирования описания \
задачи, а также присвоения ей определённых тегов. Окно редактирования открывается кнопкой "Properties".
Теги можно создавать и удалять через диалог, открывающийся из окна редактирования задачи по кнопке "Tags".
Список задач можно отсортировать по времени, потраченному на них, дате создания и имени задачи. Также присутствует \
фильтр, который позволяет настроить содержимое списка. В этом фильтре можно выбрать теги и даты. Речь идёт \
не только о датах создания задач, но и о датах, за которые данные задачи выполнялись. Дело в том, что при внесении \
любого изменения в задачу, в том числе при запуске счётчика для неё, в список связанных дат добавляется текущая дата. \
Таким образом, можно отследить, в какие даты производилась работа с данной задачей, и в дальнейшем отфильтровать \
список отображаемых задач с учётом этих дат.
В главном окне приложения можно выбрать до трёх различных задач, для каждой из которых можно запустить отдельный счётчик. \
Значения счётчика сохраняются в базу данных и в дальнейшем загружаются при следующем открытии данной задачи. \
Сбросить или как-то отредактировать значение этого счётчика из приложения нельзя.
Также в главном окне есть возможность остановить сразу все счётчики и очистить по отдельности каждое поле, \
где отображается задача.
    """