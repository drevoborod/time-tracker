#!/usr/bin/env python3

import time
import datetime
import core
import tkinter.font as fonter
from tkinter import *
from tkinter.messagebox import askquestion, askyesno
from tkinter import ttk


class TaskFrame(Frame):
    """Класс отвечает за создание рамки таски со всеми элементами."""
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        self.config(relief=GROOVE, bd=2)
        self.create_content()

    def create_content(self):
        """Создаёт содержимое окна и выполняет всю подготовительную работу."""
        self.startstopvar = StringVar()
        self.startstopvar.set("Start")
        self.task_name = None       # Создаём фейковое имя запущенной таски.
        l1 = Label(self, text='Task name:')
        big_font(l1, size=12)
        l1.grid(row=0, column=1, columnspan=3)
        self.tasklabel = TaskLabel(self, anchor=W, width=50)  # В этом поле будет название задачи.
        big_font(self.tasklabel, size=14)
        self.tasklabel.grid(row=1, column=0, columnspan=5, padx=5, pady=5)
        self.openbutton = TaskButton(self, text="Task...", command=self.name_dialogue)  # Кнопка открытия списка задач.
        self.openbutton.grid(row=1, column=5, padx=5, pady=5)
        self.description = Description(self)        # Описание задачи
        self.description.grid(row=2, column=0,columnspan=6, padx=5, pady=6)
        self.startbutton = TaskButton(self, state=DISABLED, command=self.startstopbutton, textvariable=self.startstopvar)  # Кнопка "Старт"
        self.startbutton.grid(row=3, column=0, sticky='esn')
        self.timer_window = TaskLabel(self, width=10, state=DISABLED)         # Окошко счётчика.
        big_font(self.timer_window)
        self.timer_window.grid(row=3, column=1, columnspan=3, pady=5)
        self.properties = TaskButton(self, text="Properties", state=DISABLED, command=self.properties_window)   # Кнопка свойств задачи.
        self.properties.grid(row=3, column=4, sticky=E)
        self.clearbutton = TaskButton(self, text="Clear", state=DISABLED, command=self.clear)  # Кнопка очистки фрейма.
        self.clearbutton.grid(row=3, column=5)
        self.start_time = 0     # Начальное значения счётчика времени, потраченного на задачу.
        self.running_time = 0   # Промежуточное значение счётчика.
        self.running = False    # Признак того, что счётчик работает.

    def startstopbutton(self):
        """Изменяет состояние кнопки "Start/Stop". """
        if self.running:
            self.timer_stop()
        else:
            self.timer_start()

    def properties_window(self):
        """Окно редактирования свойств таски."""
        self.timer_stop()
        self.editwindow = TaskEditWindow((self.task_name, database("one", self.task_name),
                            database("one", self.task_name, field="extra")), self)    # Берём все данные о задаче.
        self.description.update_text(database("one", self.task_name, field="extra"))

    def clear(self):
        """Пересоздание содержимого окна."""
        self.timer_stop()
        for w in self.winfo_children():
            w.destroy()
        core.Params.tasks.remove(self.task_name)
        self.create_content()

    def name_dialogue(self):
        """ Диалоговое окно выбора задачи.
        """
        self.dialogue_window = TaskSelectionWindow(self)
        TaskButton(self.dialogue_window, text="Open", command=self.get_task_name).grid(row=4, column=0, padx=5, pady=5, sticky=W)
        TaskButton(self.dialogue_window, text="Cancel", command=self.dialogue_window.destroy).grid(row=4, column=4, padx=5, pady=5, sticky=E)
        self.dialogue_window.listframe.taskslist.bind("<Return>", lambda event: self.get_task_name())   # Также задача открывается по нажатию на Энтер в таблице задач.
        self.dialogue_window.listframe.taskslist.bind("<Double-1>", lambda event: self.get_task_name())   # И по даблклику.

    def get_task_name(self):
        """Функция для получения имени задачи."""
        tasks = self.dialogue_window.get_selection()
        if len(tasks) == 1:
            task_name = tasks[0]
            # Пытаемся вытащить значение счётчика для данной задачи из БД.
            db_time = database("one", task_name)
            # Если задача в базе есть, то проверяем, не открыта ли она уже в другом окне:
            if task_name not in core.Params.tasks:
                # Проверяем, не было ли запущено уже что-то в этом окне. Если было, удаляем из списка запущенных:
                if self.task_name:
                    core.Params.tasks.remove(self.task_name)
                    # Останавливаем таймер старой задачи и сохраняем состояние:
                    self.timer_stop()
                # Создаём новую задачу:
                self.prepare_task(task_name, db_time)
            else:
                # Если обнаруживаем эту задачу уже запущенной, просто закрываем окно:
                self.dialogue_window.destroy()

    def prepare_task(self, taskname, running_time=0):
        """Функция подготавливает счётчик к работе с новой таской."""
        # Добавляем имя задачи к списку запущенных:
        core.Params.tasks.add(taskname)
        self.task_name = taskname
        # сбрасываем текущее значение счётчика (на случай, если перед этой была открыта другая задача и счётчик уже что-то для неё показал).
        # Или задаём его значение согласно взятому из БД:
        self.running_time = running_time
        # Прописываем значение счётчика в окошке счётчика.
        self.timer_window.config(text=core.time_format(self.running_time))
        self.dialogue_window.destroy()
        # В поле для имени задачи прописываем имя.
        self.tasklabel.config(text=self.task_name)
        self.startbutton.config(state=NORMAL)
        self.properties.config(state=NORMAL)
        self.clearbutton.config(state=NORMAL)
        self.timer_window.config(state=NORMAL)
        self.description.update_text(database("one", taskname, field="extra"))

    def timer_update(self):
        """Обновление окошка счётчика. Обновляется раз в полсекунды."""
        self.running_time = time.time() - self.start_time
        # Собственно изменение надписи в окошке счётчика.
        self.timer_window.config(text=core.time_format(self.running_time))
        if not core.Params.stopall:  # Проверка нажатия на кнопку "Stop all"
            # Откладываем действие на полсекунды.
            # В переменную self.timer пишется ID, создаваемое методом after(), который вызывает указанную функцию через заданный промежуток.
            self.timer = self.timer_window.after(250, self.timer_update)
        else:
            self.timer_stop()

    def timer_start(self):
        """Запуск таймера."""
        if not self.running:
            core.Params.stopall = False
            # Вытаскиваем время из БД - на тот случай, если в ней уже успело обновиться значение.
            self.start_time = time.time() - database("one", self.task_name)
            self.timer_update()
            self.running = True
            self.startstopvar.set("Stop")

    def timer_stop(self):
        """Пауза таймера и сохранение его значения в БД."""
        if self.running:
            # Метод after_cancel() останавливает выполнение обратного вызова, ID которого ему передаётся.
            self.timer_window.after_cancel(self.timer)
            self.running_time = time.time() - self.start_time
            self.running = False
            self.start_time = 0
            # Записываем текущее значение таймера в БД.
            database("update", self.task_name, value=self.running_time)
            self.startstopvar.set("Start")

    def destroy(self):
        """Переопределяем функцию закрытия фрейма, чтобы состояние таймера записывалось в БД."""
        self.timer_stop()
        Frame.destroy(self)


class TaskLabel(Label):
    """Простая текстовая метка для отображения значений. Визуально углублённая."""
    def __init__(self, parent, **kwargs):
        Label.__init__(self, master=parent, relief=SUNKEN, **kwargs)


class TaskButton(Button):
    """Просто кнопка."""
    def __init__(self, parent, **kwargs):
        Button.__init__(self, master=parent, width=8, **kwargs)

class TaskList(Frame):
    """Таблица задач со скроллом."""
    def __init__(self, columns, parent=None, **options):
        Frame.__init__(self, master=parent, **options)
        self.taskslist = ttk.Treeview(self)     # Таблица.
        scroller = Scrollbar(self)
        scroller.config(command=self.taskslist.yview)           # Привязываем скролл к таблице.
        self.taskslist.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side=RIGHT, fill=Y)                       # Сначала нужно ставить скролл!
        self.taskslist.pack(fill=BOTH, expand=YES)              # Таблица - расширяемая во всех направлениях.
        self.taskslist.config(columns=tuple([col[0] for col in columns]))  # Создаём колонки и присваиваем им идентификаторы.
        for index, col in enumerate(columns):
            self.taskslist.column(columns[index][0], width=100)   # Настраиваем колонки с указанными идентификаторами.
            # Настраиваем ЗАГОЛОВКИ колонок с указанными идентификаторами.
            self.taskslist.heading(columns[index][0], text=columns[index][1], command=lambda c=columns[index][0]: self.sortlist(c, True))

    def sortlist(self, col, reverse):
        """Сортировка по клику в заголовок колонки."""
        # get_children() возвращает список ID каждой строки списка.
        # set(ID, колонка) возвращает имя каждой записи в этой колонке.
        l = [(self.taskslist.set(k, col), k) for k in self.taskslist.get_children()]
        l.sort(reverse=reverse)
        for index, value in enumerate(l):
            self.taskslist.move(value[1], '', index)
        self.taskslist.heading(col, command=lambda: self.sortlist(col, not reverse))

    def insert_tasks(self, tasks):
        # Вставляем в таблицу все строки, собственно значения в виде кортежей передаются в values=.
        i=0
        for v in tasks:
            self.taskslist.insert('', i, text="line %d" % (i + 1), values=v)
            i += 1

    def update_list(self, tasks):
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.insert_tasks(tasks)

    def focus_(self, item):
        """Выделяет указанный пункт списка."""
        self.taskslist.focus(item)
        self.taskslist.see(item)
        self.taskslist.selection_set(item)


class TaskSelectionWindow(Toplevel):
    """Окно выбора и добавления задачи."""
    def __init__(self, parent=None, **options):
        Toplevel.__init__(self, master=parent, **options)
        self.title("Task selection")
        self.minsize(width=450, height=300)         # Минимальный размер окна.
        self.grab_set()                             # Остальные окна блокируются на время открытия этого.
        Label(self, text="Enter new task's name:").grid(row=0, column=0, sticky=W, pady=5)
        self.addentry = Entry(self, width=50)             # Поле для ввода имени новой задачи.
        self.addentry.grid(row=0, column=1, columnspan=3, sticky='we')
        self.addentry.bind('<Return>', lambda event: self.add_new_task())    # По нажатию кнопки Энтер в этом поле добавляется таск.
        self.addentry.focus_set()
        self.addbutton = Button(self, text="Add task", command=self.add_new_task)   # Кнопка добавления новой задачи.
        self.addbutton.grid(row=0, column=4, sticky=W, padx=6)
        columnnames = [('taskname', 'Task name'), ('time', 'Spent time'), ('date', 'Creation date')]
        self.listframe = TaskList(columnnames, self)     # Таблица тасок со скроллом.
        self.listframe.grid(row=1, column=0, columnspan=5, pady=10, sticky='news')
        self.selbutton = TaskButton(self, text="Select all", command=self.select_all)   # Кнопка "выбрать всё".
        self.selbutton.grid(row=2, column=0, sticky=W, padx=5, pady=5)
        self.clearbutton = TaskButton(self, text="Clear all", command=self.clear_all)  # Кнопка "снять выделение".
        self.clearbutton.grid(row=2, column=1, sticky=W)
        Frame(self, width=120).grid(row=2, column=2)
        self.editbutton = TaskButton(self, text="Properties", command=self.edit)    # Кнопка "свойства"
        self.editbutton.grid(row=2, column=3, sticky=E)
        self.delbutton = TaskButton(self, text="Remove", command=self.delete)   # Кнопка "Удалить".
        self.delbutton.grid(row=2, column=4, sticky=E, padx=5, pady=5)
        Frame(self, height=20).grid(row=3, columnspan=5)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.update_list()

    def add_new_task(self):
        """Добавление новой задачи в БД."""
        task_name = self.addentry.get()
        if len(task_name) > 0:
            if database("one", task_name) is None:  # проверяем, есть ли такая задача.
                database("add", task_name)  # Если нет, до добавляем.
                dateid = update_dates(core.date_format(datetime.datetime.now()))  # Узнаём id текущей даты в таблице дат.
                database("upd", task_name, field="dates", value=str([dateid, ]))   # И добавляем его в соответствующее поле таски в виде первого пункта списка.
                database("upd", task_name, field="creation_date", value=core.date_format(datetime.datetime.now()))
                self.update_list()
                self.listframe.focus_(self.listframe.taskslist.get_children()[-1])  # Ставим фокус на последнюю строку.

    def update_list(self):
        """Обновление содержимого таблицы задач (перечитываем из БД)."""
        self.tlist = database("all")
        self.listframe.update_list([(f[0], core.time_format(f[1]), f[3]) for f in self.tlist])

    def get_selection(self):
        """Получить список выбранных пользователем пунктов таблицы. Возвращает список названий пунктов."""
        index = [int(x) for x in self.listframe.taskslist.curselection()]   # Сначала получаем список ИНДЕКСОВ выбранных позиций.
        return [self.listframe.taskslist.get(x) for x in index]  # А потом на основании этого индекса получаем уже список имён.

    def select_all(self):
        self.listframe.taskslist.selection_set(0, END)

    def clear_all(self):
        self.listframe.taskslist.selection_clear(0, END)

    def delete(self):
        """Удаление задачи из БД (и из таблицы одновременно)."""
        names = self.get_selection()
        if len(names) > 0:
            answer = askquestion("Warning", "Are you sure you want to delete selected tasks?")
            if answer == "yes":
                database("del", tuple(names))
                self.update_list()

    def edit(self):
        """Окно редактирования свойств таски."""
        index = self.listframe.taskslist.curselection()     # Получаем кортеж ИНДЕКСОВ выбранного пользователем.
        if len(index) > 0:
            TaskEditWindow(self.tlist[index[0]], self)    # Берём первый пункт из выбранных, остальные игнорим :)
            self.update_list()
            self.focus(index[0])


class TaskEditWindow(Toplevel):
    """Окно редактирования свойств задачи."""
    def __init__(self, task, parent=None, **options):
        Toplevel.__init__(self, master=parent, **options)
        self.grab_set()         # Делает все остальные окна неактивными.
        self.title("Task properties")
        self.minsize(width=400, height=300)
        taskname = Label(self, text="Task name:")
        big_font(taskname, 10)
        taskname.grid(row=0, column=1, columnspan=2, pady=5)
        self.taskname = Text(self, width=60, height=1)
        big_font(self.taskname, 9)
        self.taskname.insert(1.0, task[0])
        self.taskname.config(state=DISABLED)
        self.taskname.grid(row=1, columnspan=4, sticky='ew', padx=6)
        Frame(self, height=30).grid(row=2)
        description = Label(self, text="Description:")
        big_font(description, 10)
        description.grid(row=3, column=1, columnspan=2, pady=5)
        self.description = Text(self, width=60, height=6)
        if task[2] is not None:
            self.description.insert(1.0, task[2])
        self.description.grid(row=4, columnspan=4, sticky='ewns', padx=6)
        self.description.focus_set()
        Frame(self, height=15).grid(row=5)
        Label(self, text='Time spent:').grid(row=6, column=0, padx=5, pady=6, sticky=E)
        TaskLabel(self, text='{}'.format(core.time_format(task[1]))).grid(row=6, column=1, sticky=W)
        Frame(self, height=40).grid(row=6)
        TaskButton(self, text='Ok', command=self.update_task).grid(row=7, column=0, sticky=SW, padx=5, pady=5)   # При нажатии на эту кнопку происходит обновление данных в БД.
        TaskButton(self, text='Cancel', command=self.destroy).grid(row=7, column=3, sticky=SE, padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.wait_window()      # Ожидание закрытия этого окна, в течении которого в родителе не выполняются команды.

    def update_task(self):
        """Обновление параметров таски в БД. Пока обновляет только поле 'extra'."""
        taskdata = (self.taskname.get(1.0, END).rstrip(), self.description.get(1.0, END).rstrip())    # Имя (id) и описание задачи.
        database("update", taskdata[0], field='extra', value=taskdata[1])
        self.destroy()


class HelpWindow(Toplevel):
    def __init__(self, parent=None, **options):
        Toplevel.__init__(self, master=parent, **options)
        self.helptext = Text(self)
        self.helptext.insert(1.0, "Здесь будет помощь. Когда-нибудь.")
        self.helptext.config(state=DISABLED)
        self.helptext.grid(row=0, column=0, sticky='news')
        TaskButton(self, text='ОК', command=self.destroy).grid(row=1, column=0, sticky='e', pady=5, padx=5)

class Description(Text):
    def __init__(self, parent=None, **options):
        Text.__init__(self, width=74, height=3, bg=core.Params.colour, state=DISABLED)

    def update_text(self, text):
        """Заполнение поля с дескрипшеном."""
        self.config(state=NORMAL)
        self.delete(1.0, END)
        if text is not None:
            self.insert(1.0, text)
        self.config(state=DISABLED)



def big_font(unit, size=20):
    """Увеличение размера шрифта выбранного элемента до 20."""
    fontname = fonter.Font(font=unit['font']).actual()['family']
    unit.config(font=(fontname, size))

def helpwindow():
    HelpWindow(run)

def stopall():
    core.Params.stopall = True

def quit():
    answer = askyesno("Quit confirmation", "Do you really want to quit?")
    if answer:
        run.destroy()

def update_dates(datestring):
    """Функция добавляет дату в таблицу дат, если там её ещё нет, и в любом случае возвращает id записи."""
    dates = database("all", table="dates")
    for x in dates:
        if datestring == x[1]:
            return x[0]
    return database("id", "date", datestring, "dates")

def database(action, *args, **kwargs):
    """Манипуляции с БД в зависимости от значения текстового аргумента action."""
    base = core.Db()
    result = None
    if action == "add":
        base.add_record(*args, **kwargs)
    elif action == "id":
        result = base.add_get_id(*args)
    elif action == "one":
        result = base.find_record(*args, **kwargs)
    elif action == "all":
        result = base.find_records(**kwargs)
    elif action == "update":
        base.update_record(*args, **kwargs)
    elif action == "del":
        base.delete_record(*args, **kwargs)
    base.close()
    return result


core.Params.tasks = set()    # Глобальный набор запущенных тасок. Для защиты от дублирования.
core.Params.stopall = False  # Признак остановки всех таймеров сразу.
run = Tk()
core.Params.colour = run.cget('bg')  # Цвет фона виджетов по умолчанию.
run.title("Tasker")
run.resizable(width=FALSE, height=FALSE)    # Запрещаем изменение размера основного окна.
TaskFrame(parent=run).grid(row=0, pady=5, padx=5, ipady=3, columnspan=5)
Frame(run, height=15).grid(row=1)
TaskFrame(parent=run).grid(row=2, pady=5, padx=5, ipady=3, columnspan=5)
Frame(run, height=15).grid(row=3)
TaskFrame(parent=run).grid(row=4, pady=5, padx=5, ipady=3, columnspan=5)
TaskButton(run, text="Help", command=helpwindow).grid(row=5, column=0, sticky='sw', pady=5, padx=5)
TaskButton(run, text="Stop all", command=stopall).grid(row=5, column=2, sticky='sn', pady=5, padx=5)
TaskButton(run, text="Quit", command=quit).grid(row=5, column=4, sticky='se', pady=5, padx=5)
run.mainloop()



# ToDo: Поддержка клавиатуры (частично реализовано - в окне выбора задачи).
# ToDo: Предотвращать разблокирование интерактива основного окна после того, как закрыто одно из окон,
# вызванное из окна выбора задачи.
# ToDo: Хоткеи копипаста должны работать в любой раскладке.


