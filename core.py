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

    def find_all(self, table):
        self.exec_script('select * from {0}'.format(table))
        return self.cur.fetchall()

    def insert(self, table, fields, values):
        """Добавление записи. Fields и values должны быть кортежами по 2 записи."""
        return self.exec_script(('insert into {0} {1} values (?, ?)'.format(table, fields), values))

    def insert_task(self, name):
        """Добавление задачи и соотвествующей записи в таблицу dates."""
        date = date_format(datetime.datetime.now())     # Текущая дата в формате "ДД.ММ.ГГГГ".
        try:    # Пытаемся создать запись.
            rowid = self.exec_script(('insert into tasks (id, timer, task_name, date) values (null, 0, ?, ?)', (name, date)))
        except sqlite3.IntegrityError:   # Если задача с таким именем уже есть, то возбуждаем исключение.
            raise DbErrors("Task name already exists")
        else:
            id = self.find_by_clause("tasks", "rowid", rowid, "id")[0][0]
            self.insert("dates", ("name", "task_id"), (date, id))
            return id      # Возвращаем id записи в таблице tasks, которую добавили.

    def update(self, id, field="timer", value=0, table="tasks"):
        self.exec_script(("update {0} set {1}=? where id='{2}'".format(table, field, id), (value, )))

    def delete(self, ids, table="tasks"):
        """Удаляет несколько записей, поэтому ids должен быть кортежом."""
        if len(ids) == 1:
            i = '(%s)' % ids[0]
        else:
            i = ids
        self.exec_script("delete from {1} where id in {0}".format(i, table))

    def close(self):
        self.cur.close()
        self.con.close()


class Params:
    """Пустой класс, нужный для того, чтобы использовать в качестве хранилища переменных."""
    pass


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
                create table tasks (id integer primary key,
                task_name text unique,
                timer int,
                description text,
                date text);
                create table options (name text unique,
                value text);
                create table dates (name text,
                task_id int);
                create table tags (name text,
                task_id int);
                """