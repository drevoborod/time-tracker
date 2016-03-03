from tkinter import *
from tkinter.ttk import Treeview


def sort(col, reverse):
    # get_children() возвращает список ID каждой строки списка.
    # set(ID, колонка) возвращает имя каждой записи в этой колонке.
    print(col)
    if col == 'two':
        l = [(int(tree.set(k, col)), k) for k in tree.get_children()]
    else:
        l = [(tree.set(k, col), k) for k in tree.get_children()]
    l.sort(reverse=reverse)
    for index, value in enumerate(l):
        print(index, "=", value)
        tree.move(value[1], '', index)
    tree.heading(col, command=lambda: sort(col, not reverse))


tasks = [('task1', 10), ('task2', 6), ('task3', 12)]

cols = {'one': 'Task name', 'two': 'Time spent'}

root = Tk()
tree = Treeview(root)
print(tuple(cols.keys()))
tree.config(columns=tuple(cols.keys()))
for col in tuple(cols.keys()):
    tree.column(col, width=100)
    tree.heading(col, text=cols[col], command=lambda c=col: sort(c, True))
#tree.heading('one', text="Task name", command=lambda: sort('one', True))
#tree.heading('two', text="Spent time", command=lambda: sort('two', True))
i=0
for n, t in tasks:
    tree.insert('', i, text="line %d" % (i + 1), values=(n, t))
    i += 1
tree.grid(sticky='news')
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
root.mainloop()