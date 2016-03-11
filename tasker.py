#!/usr/bin/env python3

import time
import core
import tkinter.font as fonter
import tkinter as tk
from tkinter.messagebox import askquestion, askyesno
from tkinter import ttk

class Db_operations():
    """Класс-мостик для работы с БД."""
    def __init__(self):
        self.db = core.Db()


class TaskFrame(tk.Frame, Db_operations):
    """Класс отвечает за создание рамки таски со всеми элементами."""
    def __init__(self, parent=None):
        tk.Frame.__init__(self, parent, relief='groove', bd=2)
        Db_operations.__init__(self)
        self.create_content()

    def create_content(self):
        """Создаёт содержимое окна и выполняет всю подготовительную работу."""
        self.startstopvar = tk.StringVar()     # Надпись на кнопке "Start".
        self.startstopvar.set("Start")
        self.task = None       # Создаём фейковое имя запущенной таски.
        l1 = tk.Label(self, text='Task name:')
        big_font(l1, size=12)
        l1.grid(row=0, column=1, columnspan=3)
        self.tasklabel = TaskLabel(self, anchor='w', width=50)  # В этом поле будет название задачи.
        big_font(self.tasklabel, size=14)
        self.tasklabel.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky='w')
        self.openbutton = TaskButton(self, text="Task...", command=self.name_dialogue)  # Кнопка открытия списка задач.
        self.openbutton.grid(row=1, column=5, padx=5, pady=5)
        self.description = Description(self, width=60, height=3)        # Описание задачи
        self.description.grid(row=2, column=0, columnspan=6, padx=5, pady=6, sticky='we')
        self.startbutton = TaskButton(self, state='disabled', command=self.startstopbutton, textvariable=self.startstopvar)  # Кнопка "Старт"
        self.startbutton.grid(row=3, column=0, sticky='esn')
        self.timer_window = TaskLabel(self, width=10, state='disabled')         # Окошко счётчика.
        big_font(self.timer_window)
        self.timer_window.grid(row=3, column=1, columnspan=3, pady=5)
        self.properties = TaskButton(self, text="Properties", state='disabled', command=self.properties_window)   # Кнопка свойств задачи.
        self.properties.grid(row=3, column=4, sticky='e')
        self.clearbutton = TaskButton(self, text="Clear", state='disabled', command=self.clear)  # Кнопка очистки фрейма.
        self.clearbutton.grid(row=3, column=5)
        self.start_time = 0     # Начальное значение счётчика времени, потраченного на задачу.
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
        self.editwindow = TaskEditWindow(self.task[0], self)    # Передаём id задачи.
        self.update_description()

    def clear(self):
        """Пересоздание содержимого окна."""
        self.timer_stop()
        for w in self.winfo_children():
            w.destroy()
        core.Params.tasks.remove(self.task[0])
        self.create_content()

    def name_dialogue(self):
        """ Диалоговое окно выбора задачи.
        """
        self.dialogue_window = TaskSelectionWindow(self)
        TaskButton(self.dialogue_window, text="Open", command=self.get_task_name).grid(row=5, column=0, padx=5, pady=5, sticky='w')
        TaskButton(self.dialogue_window, text="Cancel", command=self.dialogue_window.destroy).grid(row=5, column=4, padx=5, pady=5, sticky='e')
        self.dialogue_window.listframe.taskslist.bind("<Return>", lambda event: self.get_task_name())   # Также задача открывается по нажатию на Энтер в таблице задач.
        self.dialogue_window.listframe.taskslist.bind("<Double-1>", lambda event: self.get_task_name())   # И по даблклику.

    def get_task_name(self):
        """Функция для получения имени задачи."""
        tasks = self.dialogue_window.listframe.taskslist.selection()
        if len(tasks) == 1:
            task_id = self.dialogue_window.tdict[tasks[0]][0]    # :))
            task = self.db.find_by_clause("tasks", "id", task_id, "*")[0]  # Получаем данные о таске из БД.
            # Проверяем, не открыта ли задача уже в другом окне:
            if task_id not in core.Params.tasks:
                if self.task:                  # Проверяем, не было ли запущено уже что-то в этом окне.
                    core.Params.tasks.remove(self.task[0])  # Если было, удаляем из списка запущенных.
                    # Останавливаем таймер старой задачи и сохраняем состояние:
                    self.timer_stop()
                # Создаём новую задачу:
                self.prepare_task(task)
            else:
                # Если обнаруживаем эту задачу уже запущенной, просто закрываем окно:
                self.dialogue_window.destroy()

    def prepare_task(self, task):
        """Функция подготавливает счётчик к работе с новой таской."""
        # Добавляем имя задачи к списку запущенных:
        core.Params.tasks.add(task[0])
        self.task = list(task)
        # Задаём значение счётчика согласно взятому из БД:
        self.running_time = self.task[2]
        # Прописываем значение счётчика в окошке счётчика.
        self.timer_window.config(text=core.time_format(self.running_time))
        self.dialogue_window.destroy()      # Закрываем диалоговое окно выбора задачи.
        # В поле для имени задачи прописываем имя.
        self.tasklabel.config(text=self.task[1])
        self.startbutton.config(state='normal')
        self.properties.config(state='normal')
        self.clearbutton.config(state='normal')
        self.timer_window.config(state='normal')
        self.description.update_text(self.task[3])

    def timer_update(self, counter=0):
        """Обновление окошка счётчика. Обновляется раз в полсекунды."""
        interval = 250      # Задержка в мс, происходящая перед очередным запуском функции.
        self.running_time = time.time() - self.start_time
        # Собственно изменение надписи в окошке счётчика.
        self.timer_window.config(text=core.time_format(self.running_time))
        if not core.Params.stopall:  # Проверка нажатия на кнопку "Stop all"
            if counter >= 60000:    # Раз в минуту сохраняем значение таймера в БД.
                self.db.update_task(self.task[0], value=self.running_time)
                counter = 0
            else:
                counter += interval
            # Откладываем действие на заданный интервал.
            # В переменную self.timer пишется ID, создаваемое методом after(), который вызывает указанную функцию через заданный промежуток.
            self.timer = self.timer_window.after(250, self.timer_update, counter)
        else:
            self.timer_stop()

    def timer_start(self):
        """Запуск таймера."""
        if not self.running:
            core.Params.stopall = False
            # Вытаскиваем время из БД - на тот случай, если в ней уже успело обновиться значение.
            self.start_time = time.time() - self.db.find_by_clause("tasks", "id", self.task[0], "timer")[0][0]
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
            self.db.update_task(self.task[0], value=self.running_time)
            self.task[2] = self.running_time
            self.startstopvar.set("Start")
            self.update_description()

    def update_description(self):
        self.task[3] = self.db.find_by_clause("tasks", "id", self.task[0], "description")[0][0]
        self.description.update_text(self.task[3])

    def destroy(self):
        """Переопределяем функцию закрытия фрейма, чтобы состояние таймера записывалось в БД."""
        self.timer_stop()
        tk.Frame.destroy(self)


class TaskLabel(tk.Label):
    """Простая текстовая метка для отображения значений. Визуально углублённая."""
    def __init__(self, parent, **kwargs):
        super().__init__(master=parent, relief='sunken', **kwargs)


class TaskButton(tk.Button):
    """Просто кнопка."""
    def __init__(self, parent, **kwargs):
        super().__init__(master=parent, width=8, **kwargs)


class TaskList(tk.Frame):
    """Таблица задач со скроллом."""
    def __init__(self, columns, parent=None, **options):
        super().__init__(master=parent, **options)
        self.taskslist = ttk.Treeview(self)     # Таблица.
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.taskslist.yview)           # Привязываем скролл к таблице.
        self.taskslist.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side='right', fill='y')                       # Сначала нужно ставить скролл!
        self.taskslist.pack(fill='both', expand=1)              # Таблица - расширяемая во всех направлениях.
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
        for i, v in enumerate(tasks):
            self.taskslist.insert('', i, text=i, values=v)      # item, number, value

    def update_list(self, tasks):
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.insert_tasks(tasks)

    def focus_(self, item):
        """Выделяет указанный пункт списка."""
        self.taskslist.focus(item)
        self.taskslist.see(item)
        self.taskslist.selection_set(item)


class TaskSelectionWindow(tk.Toplevel, Db_operations):
    """Окно выбора и добавления задачи."""
    def __init__(self, parent=None, **options):
        tk.Toplevel.__init__(self, master=parent, **options)
        Db_operations.__init__(self)
        self.title("Task selection")
        self.minsize(width=450, height=300)         # Минимальный размер окна.
        self.grab_set()                             # Остальные окна блокируются на время открытия этого.
        tk.Label(self, text="New task:").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.addentry = tk.Entry(self, width=50)             # Поле для ввода имени новой задачи.
        self.addentry.grid(row=0, column=1, columnspan=3, sticky='we')
        self.addentry.bind('<Return>', lambda event: self.add_new_task())    # По нажатию кнопки Энтер в этом поле добавляется таск.
        self.addentry.focus_set()
        self.addbutton = tk.Button(self, text="Add task", command=self.add_new_task)   # Кнопка добавления новой задачи.
        self.addbutton.grid(row=0, column=4, sticky='e', padx=6, pady=5)
        columnnames = [('taskname', 'Task name'), ('time', 'Spent time'), ('date', 'Creation date')]
        self.listframe = TaskList(columnnames, self)     # Таблица тасок со скроллом.
        self.listframe.grid(row=1, column=0, columnspan=5, pady=10, sticky='news')
        tk.Label(self, text="Summary time:").grid(row=2, column=0, pady=5, padx=5, sticky='w')
        self.fulltime = TaskLabel(self, width=10)       # Общее время
        self.fulltime.grid(row=2, column=1, padx=6, pady=5, sticky='e')
        self.description = Description(self, height=4)      # Описание выбранной задачи.
        self.description.grid(row=2, column=2, rowspan=2, pady=5, padx=5, sticky='news')
        self.selbutton = TaskButton(self, text="Select all", command=self.select_all)   # Кнопка "выбрать всё".
        self.selbutton.grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.clearbutton = TaskButton(self, text="Clear all", command=self.clear_all)  # Кнопка "снять выделение".
        self.clearbutton.grid(row=3, column=1, sticky='e', padx=5, pady=5)
        self.editbutton = TaskButton(self, text="Properties", command=self.edit)    # Кнопка "свойства"
        self.editbutton.grid(row=2, column=3, sticky='w', padx=5, pady=5)
        self.delbutton = TaskButton(self, text="Remove", command=self.delete)   # Кнопка "Удалить".
        self.delbutton.grid(row=3, column=3, sticky='w', padx=5, pady=5)
        self.exportbutton = TaskButton(self, text="Export...")      # Кнопка экспорта.
        self.exportbutton.grid(row=3, column=4, padx=5, pady=5, sticky='e')
        self.filterbutton = TaskButton(self, text="Filter...")      # Кнопка фильтра.
        self.filterbutton.grid(row=2, column=4, padx=5, pady=5, sticky='e')
        tk.Frame(self, height=40).grid(row=4, columnspan=5, sticky='news')
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.update_list()
        self.update_description()

    def add_new_task(self):
        """Добавление новой задачи в БД."""
        task_name = self.addentry.get()
        if len(task_name) > 0:
            try:
                self.db.insert_task(task_name)
            except core.DbErrors as err:
                print(err)
            else:
                self.update_list()
                self.listframe.focus_(self.listframe.taskslist.get_children()[-1])  # Ставим фокус на последнюю строку.
                self.listframe.taskslist.focus_set()

    def update_list(self):
        """Обновление содержимого таблицы задач (перечитываем из БД)."""
        tlist = self.db.find_all("tasks")
        self.listframe.update_list([(f[1], core.time_format(f[2]), f[4]) for f in tlist])
        self.tdict = {}     # Словарь соответствий индексов строчек в таблице и инфы о тасках.
        i = 0
        for id in self.listframe.taskslist.get_children():
            self.tdict[id] = tlist[i]
            i += 1
        self.fulltime.config(text=core.time_format(sum([x[2] for x in tlist])))

    def update_description(self):
        sel = self.listframe.taskslist.selection()
        if len(sel) > 0:
            self.description.update_text(self.tdict[sel[0]][3])
        self.timer = self.description.after(250, self.update_description)

    def select_all(self):
        self.listframe.taskslist.selection_set(self.listframe.taskslist.get_children())

    def clear_all(self):
        self.listframe.taskslist.selection_remove(self.listframe.taskslist.get_children())

    def delete(self):
        """Удаление задачи из БД (и из таблицы одновременно)."""
        ids = [self.tdict[x][0] for x in self.listframe.taskslist.selection()]
        if len(ids) > 0:
            answer = askquestion("Warning", "Are you sure you want to delete selected tasks?")
            if answer == "yes":
                self.db.delete_tasks(tuple(ids))
                self.update_list()

    def edit(self):
        """Окно редактирования свойств таски."""
        id_name = [(self.tdict[x][0], self.tdict[x][1]) for x in self.listframe.taskslist.selection()]     # Получаем список из кортежей id тасок, выбранных пользователем, и их имён.
        if len(id_name) > 0:
            TaskEditWindow(id_name[0][0], self)    # Берём первый пункт из выбранных, остальные игнорим :)
            self.update_list()
            for i in self.listframe.taskslist.get_children():   # Находим строчку с таким же именем и выделяем её.
                if self.listframe.taskslist.item(i)["values"][0] == id_name[0][1]:
                    self.listframe.focus_(i)
                    break


class TaskEditWindow(tk.Toplevel, Db_operations):
    """Окно редактирования свойств задачи."""
    def __init__(self, taskid, parent=None, **options):
        tk.Toplevel.__init__(self, master=parent, **options)
        Db_operations.__init__(self)
        self.task = self.db.find_by_clause("tasks", "id", taskid, "*")[0]
        dates = [x[0] for x in self.db.find_by_clause("dates", "task_id", taskid, "date")]
        self.grab_set()         # Делает все остальные окна неактивными.
        self.title("Task properties")
        self.minsize(width=400, height=300)
        taskname = tk.Label(self, text="Task name:")
        big_font(taskname, 10)
        taskname.grid(row=0, column=0, pady=5, sticky='w')
        self.taskname = tk.Text(self, width=60, height=1, bg=core.Params.colour)
        big_font(self.taskname, 9)
        self.taskname.insert(1.0, self.task[1])
        self.taskname.config(state='disabled')
        self.taskname.grid(row=1, columnspan=4, sticky='ew', padx=6)
        tk.Frame(self, height=30).grid(row=2)
        description = tk.Label(self, text="Description:")
        big_font(description, 10)
        description.grid(row=3, column=0, pady=5, sticky='w')
        self.description = Description(self, width=60, height=6)
        self.description.config(state='normal', bg='white')
        if self.task[3] is not None:
            self.description.insert(self.task[3])
        self.description.grid(row=4, columnspan=4, sticky='ewns', padx=6)
        tk.Label(self, text='Tags:').grid(row=5, column=0, pady=5, sticky='nw')
        self.tags = Tagslist(taskid, self, orientation='horizontal')  # Список тегов с возможностью их включения.
    ##### Реализовать привязку тегов в БД!
        self.tags.grid(row=5, column=1, columnspan=2, pady=5, sticky='w')
        tk.Label(self, text='Time spent:').grid(row=6, column=0, padx=5, pady=5, sticky='e')
        TaskLabel(self, width=11, text='{}'.format(core.time_format(self.task[2]))).grid(row=6, column=1, pady=5, padx=5, sticky='w')
        tk.Label(self, text='Dates:').grid(row=6, column=2, sticky='w')
        datlist = Description(self, height=3, width=30)
        datlist.update_text(', '.join(dates))
        datlist.grid(row=6, column=3, rowspan=3, sticky='ew', padx=5, pady=5)
        tk.Frame(self, height=40).grid(row=9)
        TaskButton(self, text='Ok', command=self.update_task).grid(row=10, column=0, sticky='sw', padx=5, pady=5)   # При нажатии на эту кнопку происходит обновление данных в БД.
        TaskButton(self, text='Cancel', command=self.destroy).grid(row=10, column=3, sticky='se', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=10)
        self.grid_rowconfigure(4, weight=1)
        self.description.text.focus_set()       # Ставим фокус в окошко с описанием.
        self.wait_window()      # Ожидание закрытия этого окна, в течении которого в родителе не выполняются команды.

    def update_task(self):
        """Обновление параметров таски в БД. Пока обновляет только поле 'description'."""
        taskdata = (self.taskname.get(1.0, 'end').rstrip(), self.description.get().rstrip())    # Имя (id) и описание задачи.
        self.db.update_task(self.task[0], field='description', value=taskdata[1])
        self.destroy()


class HelpWindow(tk.Toplevel):
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.helptext = tk.Text(self)
        self.helptext.insert(1.0, "Здесь будет помощь. Когда-нибудь.")
        self.helptext.config(state='disabled')
        self.helptext.grid(row=0, column=0, sticky='news')
        TaskButton(self, text='ОК', command=self.destroy).grid(row=1, column=0, sticky='e', pady=5, padx=5)

class Description(tk.Frame):
    def __init__(self, parent=None, **options):
        super().__init__(master=parent)
        self.text = tk.Text(self, bg=core.Params.colour, state='disabled', wrap='word', **options)
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.text.yview)           # Привязываем скролл к тексту.
        self.text.config(yscrollcommand=scroller.set)      # Привязываем текст к скроллу :)
        scroller.grid(row=0, column=1, sticky='ns')
        self.text.grid(row=0, column=0, sticky='news')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure('all', weight=1)

    def config(self, cnf=None, **kw):
        self.text.config(cnf=cnf, **kw)

    def insert(self, text):
        self.text.insert(1.0, text)

    def get(self):
        return self.text.get(1.0, 'end')

    def update_text(self, text):
        """Заполнение поля с дескрипшеном."""
        self.config(state='normal')
        self.text.delete(1.0, 'end')
        if text is not None:
            self.text.insert(1.0, text)
        self.config(state='disabled')


class ScrolledList(tk.Frame):
    """Список со скроллом."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.table = tk.Listbox(self, selectmode='extended')     # Таблица с включённым режимом множественного выделения по Control/Shift
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.table.yview)           # Привязываем скролл к таблице.
        self.table.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side='right', fill='y')                   # Сначала нужно ставить скролл!
        self.table.pack(fill='both', expand=1)


class ScrolledCanvas(tk.Frame):
    """Прокручиваемый Canvas."""
    def __init__(self, parent=None, orientation="vertical", **options):
        super().__init__(master=parent, **options)
        scroller = tk.Scrollbar(self, orient=orientation)
        self.canvbox = tk.Canvas(self, width=(300 if orientation == "horizontal" else 100),
                              height=(30 if orientation == "horizontal" else 100))
        scroller.config(command=(self.canvbox.xview if orientation == "horizontal" else self.canvbox.yview))
        if orientation == "horizontal":
            self.canvbox.config(xscrollcommand=scroller.set)
            scroller.grid(row=1, column=0, sticky='ew')
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure('all', weight=1)
        else:
            self.canvbox.config(yscrollcommand=scroller.set)
            scroller.grid(row=0, column=1, sticky='ns')
            self.grid_rowconfigure('all', weight=1)
            self.grid_columnconfigure(0, weight=1)
        self.content_frame = tk.Frame(self.canvbox)
        self.content_frame.pack(fill='both', expand=1)
        self.canvbox.create_window((0,0), window=self.content_frame, anchor='nw')
        self.content_frame.bind("<Configure>", lambda event: self.reconf_canvas())
        self.canvbox.grid(row=0, column=0, sticky='news')

    def reconf_canvas(self):
        """Изменение размера области прокрутки Canvas."""
        self.canvbox.configure(scrollregion=self.canvbox.bbox('all'))


class Tagslist(ScrolledCanvas, Db_operations):
    """Список тегов."""
    def __init__(self, taskid, parent=None, orientation="vertical", **options):
        ScrolledCanvas.__init__(self, parent=parent, orientation=orientation, **options)
        Db_operations.__init__(self)
        self.states_dict = self.db.tags_dict(taskid)    # Словарь id тегов с состояниями для данной таски и именами.
        for key in self.states_dict:
            state = self.states_dict[key][0]
            self.states_dict[key][0] = tk.IntVar()
            cb = tk.Checkbutton(self.content_frame, text=self.states_dict[key][1], variable=self.states_dict[key][0])
            cb.pack(side=('left' if orientation == "horizontal" else 'bottom'), anchor='w')
            self.states_dict[key][0].set(state)


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


core.Params.tasks = set()    # Глобальный набор запущенных тасок. Для защиты от дублирования.
core.Params.stopall = False  # Признак остановки всех таймеров сразу.
run = tk.Tk()
core.Params.colour = run.cget('bg')  # Цвет фона виджетов по умолчанию.
run.title("Tasker")
run.resizable(width=0, height=0)    # Запрещаем изменение размера основного окна.
TaskFrame(parent=run).grid(row=0, pady=5, padx=5, ipady=3, columnspan=5)
tk.Frame(run, height=15).grid(row=1)
TaskFrame(parent=run).grid(row=2, pady=5, padx=5, ipady=3, columnspan=5)
tk.Frame(run, height=15).grid(row=3)
TaskFrame(parent=run).grid(row=4, pady=5, padx=5, ipady=3, columnspan=5)
TaskButton(run, text="Help", command=helpwindow).grid(row=5, column=0, sticky='sw', pady=5, padx=5)
TaskButton(run, text="Stop all", command=stopall).grid(row=5, column=2, sticky='sn', pady=5, padx=5)
TaskButton(run, text="Quit", command=quit).grid(row=5, column=4, sticky='se', pady=5, padx=5)
run.mainloop()




# ToDo: Поддержка клавиатуры (частично реализовано - в окне выбора задачи).
# ToDo: Предотвращать разблокирование интерактива основного окна после того, как закрыто одно из окон,
# вызванное из окна выбора задачи.
# ToDo: Хоткеи копипаста должны работать в любой раскладке.
# ToDo: Сделать так, чтобы в окне выбора задачи можно было скроллить Description (он обновляется по таймеру, поэтому скроллить невозможно).


