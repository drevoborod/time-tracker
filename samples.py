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
                create table tasks (id integer primary key autoincrement,
                task_name text unique,
                timer int,
                description text,
                creation_date text);
                create table options (option_name text unique,
                value text);
                create table dates (date text,
                task_id int);
                create table tags (tag_id text,
                task_id int);
                create table tagnames (tag_name text unique,
                tag_id integer autoincrement);
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
# Окно редактирования таски, даты: select date from dates where task_id=<id>
# Окно редактирования таски, теги, колонка "имена тегов": select tag_name from tagnames
# Окно редактирования таски, теги, колонка "выбранные теги"(галки): select tag_id from tagnames join tags on tags.task_id=<id>
# Окно добавления/удаления тегов: select tag_name from tagnames
# Окно фильтра, список дат: select distinct date from dates
# Окно фильтра, список тегов: select tag_name from tagnames
# Список задач с условием: select id, task_name, timer, description, creation_date from tasks join dates on dates.task_id = tasks.id where dates.date = '09.03.2016'
# Или так: select id, task_name, timer, description, creation_date from tasks join dates on dates.task_id = tasks.id left join tags on tags.task_id = tasks.id where dates.date in ('09.03.2016', '08.03.2016') and tags.task_id in (1,3);

import tkinter as tk

class Example(tk.Frame):
    def __init__(self, root):

        tk.Frame.__init__(self, root)
        self.canvas = tk.Canvas(root, borderwidth=0, background="#ffffff")
        self.frame = tk.Frame(self.canvas, background="#ffffff")
        self.vsb = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4,4), window=self.frame, anchor="nw",
                                  tags="self.frame")

        self.frame.bind("<Configure>", self.onFrameConfigure)

        self.populate()

    def populate(self):
        '''Put in some fake data'''
        for row in range(100):
            tk.Label(self.frame, text="%s" % row, width=3, borderwidth="1",
                     relief="solid").grid(row=row, column=0)
            t="this is the second column for row %s" %row
            tk.Label(self.frame, text=t).grid(row=row, column=1)

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

if __name__ == "__main__":
    root=tk.Tk()
    Example(root).pack(side="top", fill="both", expand=True)
    root.mainloop()