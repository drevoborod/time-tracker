#!/usr/bin/env python3

import os
import time
import datetime

import sqlite3


class DbErrors(Exception):
    """Base class for errors in database operations."""
    pass


class Db:
    """Class for interaction with database."""
    def __init__(self):
        self.db_filename = TABLE_FILE
        self.con = sqlite3.connect(self.db_filename)
        self.cur = self.con.cursor()

    def exec_script(self, script):
        """Custom script execution and commit. Returns lastrowid. Raises DbErrors on database exceptions."""
        try:
            if not isinstance(script, tuple):
                self.cur.execute(script)
            else:
                self.cur.execute(script[0], script[1])
        except sqlite3.DatabaseError as err:
            raise DbErrors(err)
        else:
            self.con.commit()
            return self.cur.lastrowid

    def find_by_clause(self, table, field, value, searchfield):
        """Returns "searchfield" if field=value. """
        self.exec_script('select {3} from {0} where {1}="{2}"'.format(table, field, value, searchfield))
        return self.cur.fetchall()

    def find_all(self, table, sortfield=None):
        """Returns all contents for given tablename."""
        if not sortfield:
            self.exec_script('select * from {0}'.format(table))
        else:
            self.exec_script('select * from {0} order by {1} asc'.format(table, sortfield))
        return self.cur.fetchall()

    def insert(self, table, fields, values):
        """Insert into fields given values. Fields and values should be 2-tuples."""
        return self.exec_script(('insert into {0} {1} values (?, ?)'.format(table, fields), values))

    def insert_task(self, name):
        """Insert task into database."""
        date = date_format(datetime.datetime.now())     # Current date in "DD.MM.YYYY" format.
        try:
            rowid = self.exec_script(('insert into tasks (id, timer, task_name, creation_date) values (null, 0, ?, ?)', (name, date)))
        except sqlite3.IntegrityError:
            raise DbErrors("Task name already exists")
        else:
            task_id = self.find_by_clause("tasks", "rowid", rowid, "id")[0][0]
            self.insert("dates", ("date", "task_id"), (date, task_id))
            self.insert("tags", ("tag_id", "task_id"), (1, task_id))
            return task_id

    def update(self, field_id, field="timer", value=0, table="tasks", updfiled="id"):
        """Updates given field in given table with given id using given value :) """
        self.exec_script(("update {0} set {1}=? where {3}='{2}'".format(table, field, field_id, updfiled), (value, )))

    def update_task(self, task_id, field="timer", value=0):
        """Updates some fields for given task id.
        If a task does not have record in dates table, a record will be created.
        """
        date = date_format(datetime.datetime.now())
        if date not in [x[0] for x in self.find_by_clause(table="dates", field="task_id", value=task_id, searchfield="date")]:
            self.insert("dates", ("date", "task_id"), (date, task_id))
        self.update(task_id, field=field, value=value)

    def delete(self, ids, field="id", table="tasks"):
        """Removes several records. ids should be a tuple."""
        if len(ids) == 1:
            i = "('%s')" % ids[0]
        else:
            i = ids
        self.exec_script("delete from {1} where {2} in {0}".format(i, table, field))

    def delete_tasks(self, ids):
        """Removes task and all corresponding records."""
        self.delete(ids)
        self.delete(ids, field="task_id", table="dates")
        self.delete(ids, field="task_id", table="timestamps")
        self.delete(ids, field="task_id", table="tags")

    def tags_dict(self, taskid):
        """Creates a list of tag ids, their values in (0, 1) and their names for given task id.
        Tag has value 1 if a record for given task id exists in tags table.
        """
        tagnames = self.find_all("tagnames", sortfield="tag_name")     # [(tagname, 1), (tagname, 2)]
        self.exec_script("select t1.tag_id from tags as t1 join tagnames as t2 on t1.tag_id = t2.tag_id where t1.task_id=%d" % taskid)
        actual_tags = [x[0] for x in self.cur.fetchall()]    # [1, 3, ...]
        states_list = []        # [[1, [1, 'tag1']],  [2, [0, 'tag2']], [3, [1, 'tag3']]]
        for k in tagnames:
            states_list.append([k[1], [1 if k[1] in actual_tags else 0, k[0]]])
        return states_list

    def simple_tagslist(self):
        """Returns tags list just like tags_dict() but every tag value is 0."""
        tagslist = self.find_all("tagnames", sortfield="tag_name")
        res = [[y, [0, x]] for x, y in tagslist]
        res.reverse()       # Should be reversed to preserve order like in database.
        return res

    def timestamps(self, taskid, current_time):
        """Returns timestamps list in same format as simple_tagslist()."""
        timestamps = self.find_by_clause('timestamps', 'task_id', taskid, 'timestamp')
        res = [[x[0], [0, '{0}; {1} spent since that moment'.format(
            time_format(x[0]), time_format(current_time - x[0]))]] for x in timestamps]
        res.reverse()
        return res


class Params:
    """Empty class used as a variable storage."""
    pass


def check_database():
    """Check if database file exists."""
    if not os.path.exists(TABLE_FILE):
        with sqlite3.connect(TABLE_FILE) as con:
            con.executescript(TABLE_STRUCTURE)
            con.commit()


def export(filename, text):
    """Creates file and fills it with given text."""
    expfile = open(filename, 'w')
    expfile.write(text)
    expfile.close()


def time_format(sec):
    """Returns time string in readable format."""
    if sec < 86400:
        return time.strftime("%H:%M:%S", time.gmtime(sec))
    else:
        return time.strftime("%jd:%H:%M:%S", time.gmtime(sec))


def date_format(date):
    """Returns date in "DD.MM.YYYY" format. Accepts datetime."""
    return datetime.datetime.strftime(date, '%d.%m.%Y')


def get_help():
    """Reading help from the file."""
    try:
        with open('help.txt', encoding='UTF-8') as helpfile:
            helptext = helpfile.read()
    except Exception:
        helptext = ''
    return helptext


TABLE_FILE = 'tasks.db'
TABLE_STRUCTURE = """\
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

HELP_TEXT = get_help()
