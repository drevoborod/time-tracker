from tkinter import *
from tkinter.ttk import Treeview


def sort(col, reverse):
    # get_children() возвращает список ID каждой строки списка.
    # set(ID, колонка) возвращает имя каждой записи в этой колонке.
    print(col)
    if col == 'time':
        l = [(int(tree.set(k, col)), k) for k in tree.get_children()]
    else:
        l = [(tree.set(k, col), k) for k in tree.get_children()]
    l.sort(reverse=reverse)
    for index, value in enumerate(l):
        print(index, "=", value)
        tree.move(value[1], '', index)
    tree.heading(col, command=lambda: sort(col, not reverse))


# Строчки в будущей таблице.
tasks = [('task1', 10, '12/02/16'), ('task2', 6, 'Yesterday'), ('task3', 12, '14.12.2008')]

# Будущие колонки: (идентификатор, заголовок)
cols = [('taskname', 'Task name'), ('time', 'Time spent'), ('date', 'Start date')]

root = Tk()
tree = Treeview(root)
# Создаём колонки и присваиваем им идентификаторы.
tree.config(columns=tuple([col[0] for col in cols]))
for index, col in enumerate(cols):
    # Настраиваем колонки с указанными идентификаторами.
    tree.column(cols[index][0], width=100)
    # Настраиваем ЗАГОЛОВКИ колонок с указанными идентификаторами.
    tree.heading(cols[index][0], text=cols[index][1], command=lambda c=cols[index][0]: sort(c, True))
# Вставляем в таблицу все строки, собственно значения в виде кортежей передаются в values=.
i=0
for v in tasks:
    tree.insert('', i, text="line %d" % (i + 1), values=v)
    i += 1
tree.grid(sticky='news')
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
root.mainloop()