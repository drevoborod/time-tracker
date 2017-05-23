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
        self.connect()

    def connect(self):
        """Connection to database."""
        self.con = sqlite3.connect(self.db_filename)
        self.cur = self.con.cursor()

    def reconnect(self):
        """Used to reconnect after exception."""
        self.cur.close()
        self.con.close()
        self.connect()

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
        """Returns "searchfield" for field=value."""
        self.exec_script('SELECT {3} FROM {0} WHERE {1}="{2}"'.format(table, field, value, searchfield))
        return self.cur.fetchall()

    def find_all(self, table, sortfield=None):
        """Returns all contents for given tablename."""
        if not sortfield:
            self.exec_script('SELECT * FROM {0}'.format(table))
        else:
            self.exec_script('SELECT * FROM {0} ORDER BY {1} ASC'.format(table, sortfield))
        return self.cur.fetchall()

    def select_task(self, task_id):
        """Returns tuple of values for given task_id."""
        task = list(self.find_by_clause(searchfield='*', field='id', value=task_id, table='tasks')[0])
        # Adding full spent time:
        self.exec_script('SELECT sum(spent_time) FROM activity WHERE task_id=%s' % task_id)
        # Adding spent time on position 3:
        task.insert(2, self.cur.fetchone()[0])
        # Append today's spent time:
        self.exec_script('SELECT spent_time FROM activity WHERE task_id={0} AND '
                         'date="{1}"'.format(task_id, date_format(datetime.datetime.now())))
        today_time = self.cur.fetchone()
        if today_time:
            task.append(today_time[0])
        else:
            task.append(today_time)
        return task

    def insert(self, table, fields, values):
        """Insert into fields given values. Fields and values should be tuples with length 2 or 3."""
        return self.exec_script(('INSERT INTO {0} {1} VALUES {2}'.format(table, fields, '(?, ?)' if len(values) == 2
                                                                         else '(?, ?, ?)'), values))

    def insert_task(self, name):
        """Insert task into database."""
        date = date_format(datetime.datetime.now())
        try:
            rowid = self.insert('tasks', ('name', 'creation_date'), (name, date))
        except sqlite3.IntegrityError:
            raise DbErrors("Task name already exists")
        else:
            task_id = self.find_by_clause("tasks", "rowid", rowid, "id")[0][0]
            self.insert("activity", ("date", "task_id", "spent_time"), (date, task_id, 0))
            self.insert("tasks_tags", ("tag_id", "task_id"), (1, task_id))
            return task_id

    def update(self, field_id, field, value, table="tasks", updfiled="id"):
        """Updates given field in given table with given id using given value :) """
        self.exec_script(("UPDATE {0} SET {1}=? WHERE {3}='{2}'".format(table, field, field_id, updfiled), (value, )))

    def update_task(self, task_id, field="spent_time", value=0):
        """Updates some fields for given task id."""
        if field == 'spent_time':
            self.exec_script("SELECT rowid FROM activity WHERE task_id={0} "
                             "AND date='{1}'".format(task_id, date_format(datetime.datetime.now())))
            daterow = self.cur.fetchone()[0]
            self.update(daterow, table='activity', updfiled='rowid', field=field, value=value)
        else:
            self.update(task_id, field=field, value=value)

    def delete(self, table="tasks", **field_values):
        """Removes several records using multiple "field in (values)" clauses.
        field_values has to be a dictionary which values can be tuples:
        field1=(value1, value), field2=value1, field3=(value1, value2, value3)"""
        clauses = []
        for key in field_values:
            value = field_values[key]
            if type(value) in (list, tuple):
                value = tuple(value)
                if len(value) == 1:
                    value = "('%s')" % value[0]
                clauses.append("{0} in {1}".format(key, value))
            #elif type(value) in (int, float):
            #    clauses.append("{0}={1}".format(key, value))
            else:
                clauses.append("{0}='{1}'".format(key, value))
        clauses = " AND ".join(clauses)
        if len(clauses) > 0:
            clauses = " WHERE " + clauses
        self.exec_script("DELETE FROM {0}{1}".format(table, clauses))

    def delete_tasks(self, values):
        """Removes task and all corresponding records. Values has to be tuple."""
        self.delete(id=values)
        self.delete(task_id=values, table="activity")
        self.delete(task_id=values, table="timestamps")
        self.delete(task_id=values, table="tasks_tags")

    def tags_dict(self, taskid):
        """Creates a list of tag ids, their values in (0, 1) and their names for given task id.
        Tag has value 1 if a record for given task id exists in tags table.
        """
        tagnames = self.find_all("tags", sortfield="name")     # [(1, tagname), (2, tagname)]
        self.exec_script("SELECT t.tag_id FROM tasks_tags AS t JOIN tags ON t.tag_id=tags.id WHERE t.task_id=%d" % taskid)
        actual_tags = [x[0] for x in self.cur.fetchall()]    # [1, 3, ...]
        states_list = []        # [[1, [1, 'tag1']],  [2, [0, 'tag2']], [3, [1, 'tag3']]]
        for k in tagnames:
            states_list.append([k[0], [1 if k[0] in actual_tags else 0, k[1]]])
        return states_list

    def simple_tagslist(self):
        """Returns tags list just like tags_dict() but every tag value is 0."""
        tagslist = self.find_all("tags", sortfield="name")
        res = [[y, [0, x]] for y, x in tagslist]
        res.reverse()       # Should be reversed to preserve order like in database.
        return res

    def timestamps(self, taskid, current_time):
        """Returns timestamps list in same format as simple_tagslist()."""
        timestamps = self.find_by_clause('timestamps', 'task_id', taskid, 'timestamp')
        res = [[x[0], [0, '{0}; {1} spent since that moment'.format(
            time_format(x[0]), time_format(current_time - x[0]))]] for x in timestamps]
        res.reverse()
        return res


def check_database():
    """Check if database file exists."""
    if not os.path.exists(TABLE_FILE):
        with sqlite3.connect(TABLE_FILE) as con:
            con.executescript(TABLE_STRUCTURE)
            con.commit()
    patch_database()


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
        day = int(sec // 86400)
        if day == 1:
            return "1 day"
        else:
            return "{} days".format(day)


def date_format(date):
    """Returns formatted date. Accepts datetime or string or int/float.
    Returns string or seconds since epoch."""
    if isinstance(date, datetime.datetime):
        return datetime.datetime.strftime(date, '%d.%m.%Y')
    elif isinstance(date, str):
        return time.mktime(time.strptime(date, '%d.%m.%Y'))
    elif isinstance(date, (int, float)):
        return datetime.datetime.strftime(datetime.datetime.fromtimestamp(date), '%d.%m.%Y')
    else:
        raise DbErrors("Wrong time format.")


def get_help():
    """Reading help from the file."""
    try:
        with open('resource/help.txt', encoding='UTF-8') as helpfile:
            helptext = helpfile.read()
    except Exception:
        helptext = ''
    return helptext


def patch_database():
    """Apply patches to database."""
    con = sqlite3.connect(TABLE_FILE)
    cur = con.cursor()
    cur.execute("SELECT value FROM options WHERE name='patch_ver';")
    res = cur.fetchone()
    if not res:
        for key in sorted(PATCH_SCRIPTS):
            for script in PATCH_SCRIPTS[key]:
                con.executescript(script)
                con.commit()
        res = (1, )
    else:
        for key in sorted(PATCH_SCRIPTS):
            if int(res[0]) < key:
                for script in PATCH_SCRIPTS[key]:
                    con.executescript(script)
                    con.commit()
    if res[0] != key:
        con.executescript("UPDATE options SET value='{0}' WHERE name='patch_ver';".format(str(key)))
        con.commit()
    con.close()


HELP_TEXT = get_help()
TABLE_FILE = 'tasks.db'
TABLE_STRUCTURE = """\
                CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                creation_date TEXT);
                CREATE TABLE activity (date TEXT,
                task_id INT,
                spent_time INT);
                CREATE TABLE tasks_tags (task_id INT,
                tag_id INT);
                CREATE TABLE timestamps (timestamp INT,
                task_id INT);
                CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE);
                CREATE TABLE options (name TEXT UNIQUE,
                value TEXT);
                INSERT INTO tags VALUES (1, 'default');
                INSERT INTO options (name) VALUES ('filter');
                INSERT INTO options VALUES ('filter_tags', '');
                INSERT INTO options VALUES ('filter_dates', '');
                INSERT INTO options VALUES ('filter_operating_mode', 'AND');
                """
PATCH_SCRIPTS = {1:
                    ["INSERT INTO options VALUES ('patch_ver', '1');",
                     "INSERT INTO options VALUES ('timers_count', '3');",
                     "INSERT INTO options VALUES ('minimize_to_tray', '0');",
                     "INSERT INTO options VALUES ('always_on_top', '0');"
                     ],
                 2: ["INSERT INTO options VALUES ('version', '1.1');"
                     ],
                 3: ["UPDATE options SET value='beta_1.1' WHERE name='version';"
                     ],
                 4: ["UPDATE options SET value='1.1' WHERE name='version';"
                     ],
                 5: ["UPDATE options SET value='1.1.1' WHERE name='version';"
                     ],
                 6: ["UPDATE options SET value='1.1.2' WHERE name='version';"
                     ],
                 7: ["UPDATE options SET value='1.2_beta' WHERE name='version';"
                     ],
                 8: ["UPDATE options SET value='1.2' WHERE name='version';"
                     ],
                 9: ["UPDATE options SET value='1.2.1.' WHERE name='version';"
                     ],
                 10: ["UPDATE options SET value='1.2.2.' WHERE name='version';"
                      ],
                 11: ["INSERT INTO options VALUES ('compact_interface', '0');",
                      "UPDATE options SET value='1.2.3.' WHERE name='version';"
                      ],
                 12: ["UPDATE options SET value='1.3' WHERE name='version';",
                      "INSERT INTO options VALUES ('preserve_tasks', '0');",
                      "INSERT INTO options VALUES ('tasks', '');"
                      ]
                 }
