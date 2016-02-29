#!/usr/bin/env python3

import sqlite3
import os

class DbErrors(Exception): pass

class Db():
    def __init__(self):
        self.db_filename = "tasks.db"
        if not os.path.exists(self.db_filename):
            self.create_table()
        self.db_file = sqlite3.connect(self.db_filename)
        self.cur = self.db_file.cursor()


    def create_table(self):
        with sqlite3.connect(self.db_filename) as con:
            cur = con.cursor()
            cur.executescript("""\
                create table tasks (id text unique,
                timer int,
                extra text);
                create table config (id text unique,
                value text);"""
                             )
            cur.close()

    def exec_script(self, script):
        try:
            if type(script) is not tuple:
                self.cur.execute(script)
            else:      # На случай, если вместо простого скрипта передан скрипт + значения для подстановки.
                self.cur.execute(script[0], script[1])
        except sqlite3.DatabaseError as err:
            raise DbErrors(err)
        else:
            self.db_file.commit()

    def add_record(self, id, field="timer", value=0, table="tasks"):
        self.exec_script(("insert into {0} (id, {1}) values (?, ?)".format(table, field), (id, value)))
        #self.exec_script("insert into {3} (id, {1}) values ('{0}', {2})".format(id, field, value, table))

    def find_record(self, id, field="timer", table="tasks"):
        """Возвращает значение для поля field из записи со значением поля "id", равным id."""
        self.exec_script("select {1} from {2} where id='{0}'".format(id, field, table))
        try:
            return self.cur.fetchone()[0]
        except TypeError:
            return None

    def find_records(self, table="tasks"):
        self.exec_script("select * from {0}".format(table))
        return self.cur.fetchall()

    def update_record(self, id, field="timer", value=0, table="tasks"):
        self.exec_script(("update {0} set {1}=? where id='{2}'".format(table, field, id), (value, )))
        #self.exec_script("update {3} set {1}='{2}' where id='{0}'".format(id, field, value, table))

    def delete_record(self, id, table="tasks"):
        self.exec_script("delete from {1} where id='{0}'".format(id, table))

    def close(self):
        self.cur.close()
        self.db_file.close()