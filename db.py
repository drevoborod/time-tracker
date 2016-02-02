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
                create table tasks (id integer primary key autoincrement,
                task_name text unique,
                timer int,
                some_data text);"""
                              )
            cur.close()

    def exec_script(self, script):
        try:
            self.cur.execute(script)
        except sqlite3.DatabaseError as err:
            raise DbErrors(err)
        else:
            self.db_file.commit()

    def add_record(self, name, timer):
        self.exec_script("insert into tasks (task_name, timer) values ('{0}', {1})".format(name, timer))

    def find_record(self, name):
        self.exec_script("select timer from tasks where task_name='%s'" % name)
        return self.cur.fetchone()

    def update_record(self, name, timer):
        self.exec_script("update tasks set timer={1} where task_name='{0}'".format(name, timer))

    def close(self):
        self.cur.close()
        self.db_file.close()