#!/usr/bin/env python3

from collections import OrderedDict as odict
import datetime
import os
import sqlite3
import time


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

    def exec_script(self, script, *values):
        """Custom script execution and commit. Returns lastrowid.
        Raises DbErrors on database exceptions."""
        try:
            if not values:
                self.cur.execute(script)
            else:
                self.cur.execute(script, values)
        except sqlite3.DatabaseError as err:
            raise DbErrors(err)
        else:
            self.con.commit()
            return self.cur.lastrowid

    def find_by_clause(self, table, field, value, searchfield, order=None):
        """Returns "searchfield" for field=value."""
        order_by = ''
        if order:
            order_by = ' ORDER BY {0}'.format(order)
        self.exec_script(
            'SELECT {3} FROM {0} WHERE {1}="{2}"{4}'.format(table, field,
                                                            value, searchfield,
                                                            order_by))
        return self.cur.fetchall()

    def find_all(self, table, sortfield=None):
        """Returns all contents for given tablename."""
        if not sortfield:
            self.exec_script('SELECT * FROM {0}'.format(table))
        else:
            self.exec_script(
                'SELECT * FROM {0} ORDER BY {1} ASC'.format(table, sortfield))
        return self.cur.fetchall()

    def select_task(self, task_id):
        """Returns dictionary of values for given task_id."""
        res = self.find_by_clause(searchfield='*', field='id', value=task_id,
                                table='tasks')[0]
        task = {key: res[number] for number, key
                in enumerate(["id", "name", "descr", "creation_date"])}
        # Adding full spent time:
        self.exec_script(
            'SELECT sum(spent_time) FROM activity WHERE task_id=%s' % task_id)
        # Adding spent time on position 3:
        task["spent_total"] = self.cur.fetchone()[0]
        # Append today's spent time:
        self.exec_script(
            'SELECT spent_time FROM activity WHERE task_id={0} AND '
            'date="{1}"'.format(task_id, date_format(datetime.datetime.now())))
        today_time = self.cur.fetchone()
        task["spent_today"] = today_time[0] if today_time else 0
        return task

    def insert(self, table, fields, values):
        """Insert into fields given values.
        Fields and values should be tuples of same length."""
        placeholder = "(" + ",".join(["?"] * len(values)) + ")"
        return self.exec_script(
            'INSERT INTO {0} {1} VALUES {2}'.format(table, fields,
                                                    placeholder), *values)

    def insert_task(self, name):
        """Insert task into database."""
        date = date_format(datetime.datetime.now())
        try:
            rowid = self.insert('tasks', ('name', 'creation_date'),
                                (name, date))
        except sqlite3.IntegrityError:
            raise DbErrors("Task name already exists")
        else:
            task_id = self.find_by_clause("tasks", "rowid", rowid, "id")[0][0]
            self.insert("activity", ("date", "task_id", "spent_time"),
                        (date, task_id, 0))
            self.insert("tasks_tags", ("tag_id", "task_id"), (1, task_id))
            return task_id

    def update(self, field_id, field, value, table="tasks", updfiled="id"):
        """Updates provided field in provided table with provided id
        using provided value """
        self.exec_script(
            "UPDATE {0} SET {1}=? WHERE {3}='{2}'".format(table, field,
                                                          field_id, updfiled),
            value)

    def update_task(self, task_id, field="spent_time", value=0):
        """Updates some fields for given task id."""
        if field == 'spent_time':
            self.exec_script("SELECT rowid FROM activity WHERE task_id={0} "
                             "AND date='{1}'".format(task_id, date_format(
                datetime.datetime.now())))
            daterow = self.cur.fetchone()[0]
            self.update(daterow, table='activity', updfiled='rowid',
                        field=field, value=value)
        else:
            self.update(task_id, field=field, value=value)

    def delete(self, table="tasks", **field_values):
        """Removes several records using multiple "field in (values)" clauses.
        field_values has to be a dictionary which values can be tuples:
        field1=(value1, value), field2=value1, field3=(value1, value2, value3)
        """
        clauses = []
        for key in field_values:
            value = field_values[key]
            if type(value) in (list, tuple):
                value = tuple(value)
                clauses.append("{0} in ({1})".format(key, ",".join((map(str, value)))))
            else:
                clauses.append("{0}='{1}'".format(key, value))
        clauses = " AND ".join(clauses)
        if len(clauses) > 0:
            clauses = " WHERE " + clauses
        self.exec_script("DELETE FROM {0}{1}".format(table, clauses))

    def delete_tasks(self, values):
        """Removes task and all corresponding records. Values has to be tuple.
        """
        self.delete(id=values)
        self.delete(task_id=values, table="activity")
        self.delete(task_id=values, table="timestamps")
        self.delete(task_id=values, table="tasks_tags")

    def tasks_to_export(self, ids):
        """Prepare tasks list for export."""
        self.exec_script(
            "select name, description, activity.date, activity.spent_time "
            "from tasks join activity "
            "on tasks.id=activity.task_id where tasks.id in ({0}) "
            "order by tasks.name, activity.date".
            format(",".join(map(str, ids))))
        db_response = [{"name": item[0], "descr": item[1] if item[1] else '',
                        "date": item[2], "spent_time": item[3]}
                       for item in self.cur.fetchall()]
        prepared_data = odict()
        for item in db_response:
            if item["name"] in prepared_data:
                prepared_data[item["name"]]["dates"].append(
                    (item["date"], time_format(item["spent_time"])))
            else:
                prepared_data[item["name"]] = {
                    "descr": item['descr'],
                    "dates": [(item["date"],
                              time_format(item["spent_time"]))]}
        self.exec_script(
            "select name, fulltime from tasks join (select task_id, "
            "sum(spent_time) as fulltime "
            "from activity where task_id in ({0}) group by task_id) "
            "as act on tasks.id=act.task_id".
            format(",".join(map(str, ids))))
        for item in self.cur.fetchall():
            prepared_data[item[0]]["spent_total"] = time_format(item[1])

        result = ['Task,Description,Dates,Time,Total working time']
        for key in prepared_data:
            temp_list = [key, prepared_data[key]["descr"],
                         prepared_data[key]["dates"][0][0],
                         prepared_data[key]["dates"][0][1],
                         prepared_data[key]["spent_total"]]
            result.append(','.join(temp_list))
            if len(prepared_data[key]["dates"]) > 1:
                for i in range(1, len(prepared_data[key]["dates"])):
                    result.append(','.join(
                        ['', '', prepared_data[key]["dates"][i][0],
                         prepared_data[key]["dates"][i][1], '']))
                    i += 1
        return result

    def dates_to_export(self, ids):
        """Prepare date-based tasks list for export."""
        self.exec_script(
            "select date, tasks.name, tasks.description, "
            "spent_time from activity join tasks "
            "on activity.task_id=tasks.id where task_id in ({0}) "
            "order by date, tasks.name".
            format(",".join(map(str, ids))))
        db_response = [{"date": item[0], "name": item[1],
                        "descr": item[2] if item[2] else '',
                        "spent_time": item[3]} for item in self.cur.fetchall()]

        prepared_data = odict()
        for item in db_response:
            if item["date"] in prepared_data:
                prepared_data[item["date"]]["tasks"].append({
                    "name": item["name"], "descr": item["descr"],
                    "spent_time": time_format(item["spent_time"])})
            else:
                prepared_data[item["date"]] = {
                    "tasks": [{"name": item["name"],
                               "descr": item["descr"],
                               "spent_time": time_format(item["spent_time"])}]}
        self.exec_script(
            "select date, sum(spent_time) from activity where task_id "
            "in ({0}) group by date order by date".format(",".join(map(str,
                                                                       ids))))
        for item in self.cur.fetchall():
            prepared_data[item[0]]["spent_total"] = (time_format(item[1]))

        result = [
            'Date,Tasks,Descriptions,Time,Summarized working time']
        for key in prepared_data:
            temp_list = [key,
                         prepared_data[key]["tasks"][0]["name"],
                         prepared_data[key]["tasks"][0]["descr"],
                         prepared_data[key]["tasks"][0]["spent_time"],
                         prepared_data[key]["spent_total"]]
            result.append(','.join(temp_list))
            if len(prepared_data[key]["tasks"]) > 1:
                for i in range(1, len(prepared_data[key]["tasks"])):
                    result.append(','.join(
                        ['',
                         prepared_data[key]["tasks"][i]["name"],
                         prepared_data[key]["tasks"][i]["descr"],
                         prepared_data[key]["tasks"][i]["spent_time"],
                         '']))
                    i += 1
        return result

    def tags_dict(self, taskid):
        """Creates a list of tag ids, their values in (0, 1) and their names
        for provided task id.
        Tag has value 1 if a record for given task id exists in tags table.
        """
        # [(1, tagname), (2, tagname)]
        tagnames = self.find_all("tags", sortfield="name")
        self.exec_script("SELECT t.tag_id FROM tasks_tags AS t JOIN tags "
                         "ON t.tag_id=tags.id WHERE t.task_id=%d" % taskid)
        actual_tags = [x[0] for x in self.cur.fetchall()]  # [1, 3, ...]
        # [[1, [1, 'tag1']],  [2, [0, 'tag2']], [3, [1, 'tag3']]]
        states_list = []
        for k in tagnames:
            states_list.append([k[0], [1 if k[0] in actual_tags else 0, k[1]]])
        return states_list

    def simple_tagslist(self):
        """Returns tags list just like tags_dict() but every tag value is 0."""
        tagslist = self.find_all("tags", sortfield="name")
        res = [[y, [0, x]] for y, x in tagslist]
        res.reverse()  # Should be reversed to preserve order like in database.
        return res

    def simple_dateslist(self):
        """Returns simple list of all dates of activity without duplicates."""
        self.exec_script(
            'SELECT DISTINCT date FROM activity ORDER BY date DESC')
        return [x[0] for x in self.cur.fetchall()]

    def timestamps(self, taskid, current_time):
        """Returns timestamps list in same format as simple_tagslist()."""
        timestamps = self.find_by_clause('timestamps', 'task_id', taskid,
                                         'timestamp')
        res = [[x[0], [0, '{0}; {1} spent since that moment'.format(
            time_format(x[0]), time_format(current_time - x[0]))]] for x in
               timestamps]
        res.reverse()
        return res


def prepare_filter_query(dates, tags, mode):
    """Query to get filtered tasks data from database."""
    if mode == "OR":
        return 'SELECT id, name, total_time, description, ' \
               'creation_date FROM tasks JOIN activity ' \
               'ON activity.task_id=tasks.id JOIN tasks_tags ' \
               'ON tasks_tags.task_id=tasks.id ' \
               'JOIN (SELECT task_id, sum(spent_time) ' \
               'AS total_time ' \
               'FROM activity GROUP BY task_id) AS act ' \
               'ON act.task_id=tasks.id WHERE date IN ({1}) ' \
               'OR tag_id IN ({0}) ' \
               'GROUP BY act.task_id'. \
            format(",".join(map(str, tags)), "'%s'" % "','".join(dates))
    else:
        if dates and tags:
            return 'SELECT DISTINCT id, name, total_time, ' \
                   'description, creation_date FROM tasks  JOIN ' \
                   '(SELECT task_id, sum(spent_time) AS total_time ' \
                   'FROM activity WHERE activity.date IN ({0}) ' \
                   'GROUP BY task_id) AS act ' \
                   'ON act.task_id=tasks.id JOIN (SELECT tt.task_id' \
                   ' FROM tasks_tags AS tt WHERE ' \
                   'tt.tag_id IN ({1}) GROUP BY tt.task_id ' \
                   'HAVING COUNT(DISTINCT tt.tag_id)={3}) AS x ON ' \
                   'x.task_id=tasks.id JOIN (SELECT act.task_id ' \
                   'FROM activity AS act WHERE act.date IN ({0}) ' \
                   'GROUP BY act.task_id HAVING ' \
                   'COUNT(DISTINCT act.date)={2}) AS y ON ' \
                   'y.task_id=tasks.id'. \
                format("'%s'" % "','".join(dates),
                       ",".join(map(str, tags)), len(dates), len(tags))
        elif not dates:
            return 'SELECT DISTINCT id, name, total_time, ' \
                   'description, creation_date FROM tasks  ' \
                   'JOIN (SELECT task_id, sum(spent_time) ' \
                   'AS total_time FROM activity GROUP BY ' \
                   'task_id) AS act ON act.task_id=tasks.id ' \
                   'JOIN (SELECT tt.task_id FROM tasks_tags ' \
                   'AS tt WHERE tt.tag_id IN ({0}) GROUP BY ' \
                   'tt.task_id HAVING ' \
                   'COUNT(DISTINCT tt.tag_id)={1}) AS x ON ' \
                   'x.task_id=tasks.id'. \
                format(",".join(map(str, tags)), len(tags))
        elif not tags:
            return 'SELECT DISTINCT id, name, total_time, ' \
                   'description, creation_date FROM tasks  ' \
                   'JOIN (SELECT task_id, sum(spent_time) ' \
                   'AS total_time FROM activity WHERE activity.date' \
                   ' IN ({0}) GROUP BY task_id) AS act ' \
                   'ON act.task_id=tasks.id JOIN (SELECT ' \
                   'act.task_id FROM activity AS act ' \
                   'WHERE act.date IN ({0}) GROUP BY act.task_id ' \
                   'HAVING COUNT(DISTINCT act.date)={1}) AS y ' \
                   'ON y.task_id=tasks.id'.format("'%s'" % "','"
                                                  .join(dates), len(dates))


def check_database():
    """Check if database file exists."""
    if not os.path.exists(TABLE_FILE):
        with sqlite3.connect(TABLE_FILE) as con:
            con.executescript(TABLE_STRUCTURE)
            con.commit()
    patch_database()


def write_to_disk(filename, text):
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


def date_format(date, template='%Y-%m-%d'):
    """Returns formatted date (str). Accepts datetime."""
    return datetime.datetime.strftime(date, template)


def str_to_date(string, template='%Y-%m-%d'):
    """Returns datetime from string."""
    return datetime.datetime.strptime(string, template)


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
    key = '0'
    if not res:
        for key in sorted(PATCH_SCRIPTS):
            apply_script(PATCH_SCRIPTS[key], con)
        res = (1,)
    else:
        for key in sorted(PATCH_SCRIPTS):
            if int(res[0]) < key:
                apply_script(PATCH_SCRIPTS[key], con)
    if res[0] != key:
        con.executescript(
            "UPDATE options SET value='{0}' WHERE name='patch_ver';".format(
                str(key)))
        con.commit()
    con.close()


def apply_script(scripts_list, db_connection):
    for script in scripts_list:
        try:
            db_connection.executescript(script)
            db_connection.commit()
        except sqlite3.DatabaseError:
            pass


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
                INSERT INTO options VALUES ('patch_ver', '0');
                INSERT INTO options VALUES ('timers_count', '3');
                INSERT INTO options VALUES ('minimize_to_tray', '0');
                INSERT INTO options VALUES ('always_on_top', '0');
                INSERT INTO options VALUES ('preserve_tasks', '0');
                INSERT INTO options VALUES ('show_today', '0');
                INSERT INTO options VALUES ('toggle_tasks', '0');
                INSERT INTO options VALUES ('tasks', '');
                INSERT INTO options VALUES ('compact_interface', '0');
                INSERT INTO options VALUES ('version', '1.5');
                INSERT INTO options VALUES ('install_time', datetime('now'));
                """
# PATCH_SCRIPTS = {
# 1: [
#     "INSERT INTO options VALUES ('toggle_tasks', '0');"
# ],
# 2: [
#     "UPDATE options SET value='2.0' WHERE name='version';"
# ]
# }
PATCH_SCRIPTS = {}
