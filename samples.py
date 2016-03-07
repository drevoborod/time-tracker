import sqlite3
import datetime

class DbErrors(Exception): pass

class Db():
    def __init__(self):
        self.db_filename = ':memory:'
        self.con = sqlite3.connect(self.db_filename)
        self.create_table()
        self.cur = self.con.cursor()


    def create_table(self):
        self.con.executescript(table_structure)
        self.con.commit()


    def exec_script(self, script):
        #print(script)
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

    def find(self, table, field, value, searchfield):
        """Поиск в поле searchfield по условию field=value. В качестве field может быть звёздочка."""
        self.exec_script('select {3} from {0} where {1}="{2}"'.format(table, field, value, searchfield))
        return self.cur.fetchall()

    def insert(self, table, fields, values):
        """Добавление записи. Fields и values должны быть кортежами по 2 записи."""
        return self.exec_script(('insert into {0} {1} values (?, ?)'.format(table, fields), values))

    def update(self, table, ):
        self.exec_script('update ')

    def insert_task(self, name):
        date = date_format(datetime.datetime.now())     # Текущая дата в формате "ДД.ММ.ГГГГ".
        try:    # Пытаемся создать запись.
            rowid = self.exec_script(('insert into tasks (id, task_name, creation_date) values (null, ?, ?)', (name, date)))
        except sqlite3.IntegrityError:   # Если задача с таким именем уже есть, то возбуждаем исключение.
            raise DbErrors("Task name already exists")
        else:
            id = self.find("tasks", "rowid", rowid, "id")[0][0]
            self.insert("dates", ("date", "task_id"), values=(date, id))
            return id      # Возвращаем id записи в таблице tasks, которую добавили.



def date_format(date):
    """Возвращает дату в формате ДД:ММ:ГГГГ. На вход принимает datetime."""
    return datetime.datetime.strftime(date, '%d.%m.%Y')


table_structure = """\
                create table tasks (id integer primary key,
                task_name text unique,
                timer int,
                description text,
                creation_date text);
                create table options (name text unique,
                value text);
                create table dates (date text,
                task_id int);
                create table tags (tag_name text,
                task_id int);
                """


db = Db()
db.insert_task("task1")
db.insert_task("task2")
db.insert_task("task3")
db.exec_script("insert into dates values ('12.13.2014', 3);")
#db.exec_script("select name from dates join tasks on dates.task_id = tasks.id")
db.exec_script("select * from tasks join dates on dates.task_id = tasks.id")
res = db.cur.fetchall()
print(res)
date_id = db.find("dates", "date", date_format(datetime.datetime.now()), "task_id")
print(date_id)
ids = tuple([x[0] for x in date_id])
db.exec_script("select * from tasks where id in {0}".format(ids))
print(db.cur.fetchall())
db.exec_script("select * from dates")
print(db.cur.fetchall())


# SELECT DISTINCT column1, column2,.....columnN FROM table_name WHERE [condition]: поля не повторяются
# http://www.tutorialspoint.com/sqlite/sqlite_using_joins.htm
