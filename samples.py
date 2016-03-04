from tkinter import *
from tkinter import ttk


class TaskList(Frame):
    """Таблица задач со скроллом."""
    def __init__(self, columns, parent=None, **options):
        Frame.__init__(self, master=parent, **options)
        self.columns = columns
        self.create_list()

    def create_list(self):
        self.taskslist = ttk.Treeview(self)     # Таблица.
        scroller = Scrollbar(self)
        scroller.config(command=self.taskslist.yview)           # Привязываем скролл к таблице.
        self.taskslist.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side=RIGHT, fill=Y)                       # Сначала нужно ставить скролл!
        self.taskslist.pack(fill=BOTH, expand=YES)              # Таблица - расширяемая во всех направлениях.
        self.taskslist.config(columns=tuple([col[0] for col in self.columns]))  # Создаём колонки и присваиваем им идентификаторы.
        for index, col in enumerate(self.columns):
            self.taskslist.column(self.columns[index][0], width=100)   # Настраиваем колонки с указанными идентификаторами.
            # Настраиваем ЗАГОЛОВКИ колонок с указанными идентификаторами.
            self.taskslist.heading(self.columns[index][0], text=self.columns[index][1], command=lambda c=self.columns[index][0]: self.sortlist(c, True))

    def sortlist(self, col, reverse):
        # get_children() возвращает список ID каждой строки списка.
        # set(ID, колонка) возвращает имя каждой записи в этой колонке.
        print(col)
        l = [(self.taskslist.set(k, col), k) for k in self.taskslist.get_children()]
        l.sort(reverse=reverse)
        for index, value in enumerate(l):
            print(index, "=", value)
            self.taskslist.move(value[1], '', index)
        self.taskslist.heading(col, command=lambda: self.sortlist(col, not reverse))

    def update_list(self, tasks):
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.insert_tasks(tasks)

    def insert_tasks(self, tasks):
        # Вставляем в таблицу все строки, собственно значения в виде кортежей передаются в values=.
        i=0
        for v in tasks:
            self.taskslist.insert('', i, text="line %d" % (i + 1), values=v)
            i += 1


# Строчки в будущей таблице.
tasks = [('task1', 10, '12/02/16'), ('task2', 6, 'Yesterday'), ('task3', 12, '14.12.2008')]
tasks1 = [('task1', '11:12:03', '12/02/16'), ('task2', '1d:03:06:10', 'Yesterday'), ('task3', '05:04:00', '14.12.2008'),
          ('task4', '2d:00:01:00', 'sometimes')]

# Будущие колонки: (идентификатор, заголовок)
cols = [('taskname', 'Task name'), ('time', 'Time spent'), ('date', 'Start date')]

root = Tk()
tree = TaskList(cols, root)
tree.update_list(tasks1)
tree.grid(sticky='news')
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
Button(root, text="Update", command=lambda: tree.update_list(tasks)).grid()
root.mainloop()