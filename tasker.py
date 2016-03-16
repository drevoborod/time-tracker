#!/usr/bin/env python3

import time

import tkinter.font as fonter
import tkinter as tk
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import askquestion, askyesno, showinfo
from tkinter import ttk

import core


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
        self.openbutton.grid(row=1, column=5, padx=5, pady=5, sticky='e')
        self.description = Description(self, width=60, height=3)        # Описание задачи
        self.description.grid(row=2, column=0, columnspan=6, padx=5, pady=6, sticky='we')
        self.startbutton = TaskButton(self, state='disabled', command=self.startstopbutton, textvariable=self.startstopvar)  # Кнопка "Старт"
        big_font(self.startbutton, size=14)
        self.startbutton.grid(row=3, column=0, sticky='wsn')
        self.timer_window = TaskLabel(self, width=10, state='disabled')         # Окошко счётчика.
        big_font(self.timer_window)
        self.timer_window.grid(row=3, column=1, pady=5)
        self.add_timestamp_button = TaskButton(self, text='Add\ntimestamp', width=10, state='disabled', command=self.add_timestamp)
        self.add_timestamp_button.grid(row=3, column=2, sticky='w', padx=5)
        self.timestamps_window_button = TaskButton(self, text='View\ntimestamps', width=10, state='disabled', command=self.timestamps_window)
        self.timestamps_window_button.grid(row=3, column=3, sticky='w', padx=5)
        self.properties = TaskButton(self, text="Properties", width=10, state='disabled', command=self.properties_window)   # Кнопка свойств задачи.
        self.properties.grid(row=3, column=4, sticky='e', padx=5)
        self.clearbutton = TaskButton(self, text="Clear", state='disabled', command=self.clear)  # Кнопка очистки фрейма.
        self.clearbutton.grid(row=3, column=5, sticky='e', padx=5)
        self.start_time = 0     # Начальное значение счётчика времени, потраченного на задачу.
        self.running_time = 0   # Промежуточное значение счётчика.
        self.running = False    # Признак того, что счётчик работает.

    def timestamps_window(self):
        TimestampsWindow(self.task_id, self.running_time, self)

    def add_timestamp(self):
        """Добавляем таймстемп в БД."""
        self.db.insert('timestamps', ('task_id', 'timestamp'), (self.task_id, self.running_time))
        showinfo("Timestamp added", "Timestamp added successfully.")

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
        """ Диалоговое окно выбора задачи."""
        self.dialogue_window = TaskSelectionWindow(self)
        TaskButton(self.dialogue_window, text="Open", command=self.get_task_name).grid(row=5, column=0, padx=5, pady=5, sticky='w')
        TaskButton(self.dialogue_window, text="Cancel", command=self.dialogue_window.destroy).grid(row=5, column=4, padx=5, pady=5, sticky='e')
        self.dialogue_window.listframe.taskslist.bind("<Return>", lambda event: self.get_task_name())   # Также задача открывается по нажатию на Энтер в таблице задач.
        self.dialogue_window.listframe.taskslist.bind("<Double-1>", lambda event: self.get_task_name())   # И по даблклику.

    def get_task_name(self):
        """Функция для получения имени задачи."""
        tasks = self.dialogue_window.listframe.taskslist.selection()
        if len(tasks) == 1:
            self.task_id = self.dialogue_window.tdict[tasks[0]][0]    # :))
            task = self.db.find_by_clause("tasks", "id", self.task_id, "*")[0]  # Получаем данные о таске из БД.
            # Проверяем, не открыта ли задача уже в другом окне:
            if self.task_id not in core.Params.tasks:
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
        self.add_timestamp_button.config(state='normal')
        self.timestamps_window_button.config(state='normal')
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
            print(self.running_time)
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
    def __init__(self, parent, width=8, **kwargs):
        super().__init__(master=parent, width=width, **kwargs)


class TaskList(tk.Frame):
    """Таблица задач со скроллом."""
    def __init__(self, columns, parent=None, **options):
        super().__init__(master=parent, **options)
        self.taskslist = ttk.Treeview(self, takefocus=1)     # Таблица.
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.taskslist.yview)           # Привязываем скролл к таблице.
        self.taskslist.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side='right', fill='y')                       # Сначала нужно ставить скролл!
        self.taskslist.pack(fill='both', expand=1)              # Таблица - расширяемая во всех направлениях.
        self.taskslist.config(columns=tuple([col[0] for col in columns]))  # Создаём колонки и присваиваем им идентификаторы.
        for index, col in enumerate(columns):
            self.taskslist.column(columns[index][0], width=100, minwidth=100, anchor='center')   # Настраиваем колонки с указанными идентификаторами.
            # Настраиваем ЗАГОЛОВКИ колонок с указанными идентификаторами.
            self.taskslist.heading(columns[index][0], text=columns[index][1], command=lambda c=columns[index][0]: self.sortlist(c, True))
        self.taskslist.column('#0', anchor='w', width=70, minwidth=50, stretch=0)
        self.taskslist.column('taskname', width=600, anchor='w')

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
            self.taskslist.insert('', i, text="#%d" % (i + 1), values=v)      # item, number, value

    def update_list(self, tasks):
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.insert_tasks(tasks)

    def focus_(self, item):
        """Выделяет указанный пункт списка."""
        self.taskslist.see(item)
        self.taskslist.selection_set(item)
        self.taskslist.focus_set()
        self.taskslist.focus(item)


class TaskSelectionWindow(tk.Toplevel, Db_operations):
    """Окно выбора и добавления задачи."""
    def __init__(self, parent=None, **options):
        tk.Toplevel.__init__(self, master=parent, **options)
        Db_operations.__init__(self)
        self.db.check_database()        # Here we check if database actually exists :)
        self.title("Task selection")
        self.minsize(width=450, height=300)         # Минимальный размер окна.
        self.grab_set()                             # Остальные окна блокируются на время открытия этого.
        tk.Label(self, text="New task:").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        self.addentry = tk.Entry(self, width=50)             # Поле для ввода имени новой задачи.
        self.addentry.grid(row=0, column=1, columnspan=3, sticky='we')
        self.addentry.bind('<Return>', lambda event: self.add_new_task())    # По нажатию кнопки Энтер в этом поле добавляется таск.
        self.addentry.focus_set()
        self.addbutton = tk.Button(self, text="Add task", command=self.add_new_task, takefocus=0)   # Кнопка добавления новой задачи.
        self.addbutton.grid(row=0, column=4, sticky='e', padx=6, pady=5)
        columnnames = [('taskname', 'Task name'), ('time', 'Spent time'), ('date', 'Creation date')]
        self.listframe = TaskList(columnnames, self)     # Таблица тасок со скроллом.
        self.listframe.grid(row=1, column=0, columnspan=5, pady=10, sticky='news')
        tk.Label(self, text="Summary time:").grid(row=2, column=0, pady=5, padx=5, sticky='w')
        self.fulltime_frame = TaskLabel(self, width=10)       # Общее время
        self.fulltime_frame.grid(row=2, column=1, padx=6, pady=5, sticky='e')
        self.description = Description(self, height=4)      # Описание выбранной задачи.
        self.description.grid(row=2, column=2, rowspan=2, pady=5, padx=5, sticky='news')
        selbutton = TaskButton(self, text="Select all...", width=10, command=self.select_all)   # Кнопка "выбрать всё".
        selbutton.grid(row=3, column=0, sticky='w', padx=5, pady=5)
        clearbutton = TaskButton(self, text="Clear all...", width=10, command=self.clear_all)  # Кнопка "снять выделение".
        clearbutton.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        self.editbutton = TaskButton(self, text="Properties", width=10, command=self.edit)    # Кнопка "свойства"
        self.editbutton.grid(row=2, column=3, sticky='w', padx=5, pady=5)
        self.delbutton = TaskButton(self, text="Remove", width=10, command=self.delete)   # Кнопка "Удалить".
        self.delbutton.grid(row=3, column=3, sticky='w', padx=5, pady=5)
        self.exportbutton = TaskButton(self, text="Export...", command=self.export)      # Кнопка экспорта.
        self.exportbutton.grid(row=3, column=4, padx=5, pady=5, sticky='e')
        self.filterbutton = TaskButton(self, text="Filter...", command=self.filterwindow)      # Кнопка фильтра.
        self.filterbutton.grid(row=2, column=4, padx=5, pady=5, sticky='e')
        tk.Frame(self, height=40).grid(row=4, columnspan=5, sticky='news')
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.update_list()      # Заполняем содержимое таблицы.
        self.current_task = ''      # Текущая выбранная задача.
        self.listframe.taskslist.bind("<Down>", lambda e: self.descr_down())
        self.listframe.taskslist.bind("<Up>", lambda e: self.descr_up())
        self.listframe.taskslist.bind("<Button-1>", self.descr_click)
        self.addentry.bind("<Tab>", lambda e: self.focus_first_item())

    def focus_first_item(self):
        """Ставит фокус на первой строке."""
        item = self.listframe.taskslist.get_children()[0]
        self.listframe.focus_(item)
        self.update_descr(item)

    def export(self):
        """Функция для экспорта списка задач в файл."""
        text = "Task name,Time spent, Creation date\n"
        text = text + '\n'.join(','.join([row[1], core.time_format(row[2]), row[4]]) for row in self.tdict.values())
        text = text + '\nSummary time,%s\n' % self.fulltime
        filename = asksaveasfilename(parent=self, defaultextension='.csv', filetypes=[("All files","*.*")])
        core.export(filename, text)

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
                items = {x: self.listframe.taskslist.item(x) for x in self.listframe.taskslist.get_children()}
                # Если созданная таска появилась в списке, ставим на неё курсор.
                for item in items:
                    if items[item]['values'][0] == task_name:
                        self.listframe.focus_(item)  # Ставим фокус на указанную строку.
                        break

    def update_list(self):
        """Обновление содержимого таблицы задач (перечитываем из БД)."""
        query = self.db.find_by_clause('options', 'option_name', 'filter', 'value')[0][0]   # Восстанавливаем значение фильтра.
        if query:
            self.db.exec_script(query)
            tlist = self.db.cur.fetchall()
            self.filterbutton.config(bg='lightblue')
        else:
            tlist = self.db.find_all("tasks")
            self.filterbutton.config(bg=core.Params.colour)
        self.listframe.update_list([(f[1], core.time_format(f[2]), f[4]) for f in tlist])
        self.tdict = {}     # Словарь соответствий индексов строчек в таблице и инфы о тасках.
        i = 0
        for id in self.listframe.taskslist.get_children():
            self.tdict[id] = tlist[i]
            i += 1
        self.fulltime = core.time_format(sum([x[2] for x in tlist]))
        self.fulltime_frame.config(text=self.fulltime)

    def descr_click(self, event):
        """Передаёт item, на котором стоит курсор мыши."""
        self.update_descr(self.listframe.taskslist.identify_row(event.y))

    def descr_up(self):
        """Передаёт id ПРЕДЫДУЩЕГО item относительно выбранного."""
        item = self.listframe.taskslist.focus()
        prev_item = self.listframe.taskslist.prev(item)
        if prev_item == '':
            self.update_descr(item)
        else:
            self.update_descr(prev_item)
        # Короткая запись, для истории:
        #self.update_descr(item if self.listframe.taskslist.prev(item) == '' else self.listframe.taskslist.prev(item))

    def descr_down(self):
        """Передаёт id СЛЕДУЮЩЕГО за выбранным item."""
        item = self.listframe.taskslist.focus()
        next_item = self.listframe.taskslist.next(item)
        if next_item == '':
            self.update_descr(item)
        else:
            self.update_descr(next_item)
        # Короткая запись, для истории:
        #self.update_descr(item if self.listframe.taskslist.next(item) == '' else self.listframe.taskslist.next(item))

    def update_descr(self, item):
        """Заполнение окошка с описанием выбранной задачи."""
        if item != '':
            self.description.update_text(self.tdict[item][3])

    def select_all(self):
        self.listframe.taskslist.selection_set(self.listframe.taskslist.get_children())

    def clear_all(self):
        self.listframe.taskslist.selection_remove(self.listframe.taskslist.get_children())

    def delete(self):
        """Удаление задачи из БД (и из таблицы одновременно)."""
        ids = [self.tdict[x][0] for x in self.listframe.taskslist.selection() if self.tdict[x][0] not in core.Params.tasks]
        if len(ids) > 0:
            answer = askquestion("Warning", "Are you sure you want to delete selected tasks?")
            if answer == "yes":
                self.db.delete_tasks(tuple(ids))
                self.update_list()
        self.grab_set()

    def edit(self):
        """Окно редактирования свойств таски."""
        # Получаем кортеж из id выбранной таски и её имени.
        try:
            id_name = (self.tdict[self.listframe.taskslist.focus()][0], self.tdict[self.listframe.taskslist.focus()][1])
        except KeyError:
            pass
        else:
            TaskEditWindow(id_name[0], self)
            self.update_list()
            for i in self.listframe.taskslist.get_children():   # Находим строчку с таким же именем
                if self.listframe.taskslist.item(i)["values"][0] == id_name[1]:
                    self.listframe.focus_(i)        # и выделяем её.
                    self.update_descr(i)        # Обновляем описание.
                    break
        self.grab_set()

    def filterwindow(self):
        """Открытие окна фильтров."""
        self.filteroptions = FilterWindow(self)
        self.update_list()
        self.grab_set()


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
        taskname.grid(row=0, column=0, pady=5, padx=5, sticky='w')
        self.taskname = tk.Text(self, width=60, height=1, bg=core.Params.colour)
        big_font(self.taskname, 9)
        self.taskname.insert(1.0, self.task[1])
        self.taskname.config(state='disabled')
        self.taskname.grid(row=1, columnspan=5, sticky='ew', padx=6)
        tk.Frame(self, height=30).grid(row=2)
        description = tk.Label(self, text="Description:")
        big_font(description, 10)
        description.grid(row=3, column=0, pady=5, padx=5, sticky='w')
        self.description = Description(self, width=60, height=6)
        self.description.config(state='normal', bg='white')
        if self.task[3] is not None:
            self.description.insert(self.task[3])
        self.description.grid(row=4, columnspan=5, sticky='ewns', padx=5)
        tk.Label(self, text='Tags:').grid(row=5, column=0, pady=5, padx=5, sticky='nw')
        self.tags_update()
        TaskButton(self, text='Edit tags', width=10, command=self.tags_edit).grid(row=5, column=4, padx=5, pady=5, sticky='e')
        tk.Label(self, text='Time spent:').grid(row=6, column=0, padx=5, pady=5, sticky='w')
        TaskLabel(self, width=11, text='{}'.format(core.time_format(self.task[2]))).grid(row=6, column=1, pady=5, padx=5, sticky='w')
        tk.Label(self, text='Dates:').grid(row=6, column=2, sticky='w')
        datlist = Description(self, height=3, width=30)
        datlist.update_text(', '.join(dates))
        datlist.grid(row=6, column=3, rowspan=3, columnspan=2, sticky='ew', padx=5, pady=5)
        tk.Frame(self, height=40).grid(row=9)
        TaskButton(self, text='Ok', command=self.update_task).grid(row=10, column=0, sticky='sw', padx=5, pady=5)   # При нажатии на эту кнопку происходит обновление данных в БД.
        TaskButton(self, text='Cancel', command=self.destroy).grid(row=10, column=4, sticky='se', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=10)
        self.grid_rowconfigure(4, weight=1)
        self.description.text.focus_set()       # Ставим фокус в окошко с описанием.
        self.wait_window()      # Ожидание закрытия этого окна, в течении которого в родителе не выполняются команды.

    def tags_edit(self):
        """Открывает окно редактирования списка тегов."""
        TagsEditWindow(self)
        self.tags_update()
        self.grab_set()

    def tags_update(self):
        """Отображает список тегов."""
        self.tags = Tagslist(self.db.tags_dict(self.task[0]), self, orientation='horizontal')  # Список тегов с возможностью их включения.
        self.tags.grid(row=5, column=1, columnspan=3, pady=5, padx=5, sticky='we')

    def update_task(self):
        """Обновление параметров таски в БД."""
        taskdata = self.description.get().rstrip()    # описание задачи.
        self.db.update_task(self.task[0], field='description', value=taskdata)
        for item in self.tags.states_list:   # Также обновляем набор тегов для таски.
            if item[1][0].get() == 1:
                self.db.insert('tags', ('task_id', 'tag_id'), (self.task[0], item[0]))
            else:
                self.db.exec_script('delete from tags where task_id={0} and tag_id={1}'.format(self.task[0], item[0]))
        self.destroy()


class TagsEditWindow(tk.Toplevel, Db_operations):
    """Шаблон окна редактирования какого-нибудь списка чекбаттонов."""
    def __init__(self, parent=None, **options):
        tk.Toplevel.__init__(self, master=parent, **options)
        Db_operations.__init__(self)
        self.grab_set()
        self.addentry()
        self.tags_update()
        self.window_elements_config()
        TaskButton(self, text='Close', command=self.destroy).grid(row=2, column=0, pady=5, padx=5, sticky='w')
        TaskButton(self, text='Delete', command=self.delete).grid(row=2, column=2, pady=5, padx=5, sticky='e')
        self.wait_window()

    def window_elements_config(self):
        """Настройка параметров окна."""
        self.title("Tags editor")
        self.minsize(width=200, height=200)

    def addentry(self):
        """Создание поля для ввода нового элемента. При наследовании может быть заменён пустой функцией, тогда поля не будет."""
        self.addentry_label = tk.Label(self, text="Add tag:")
        self.addentry_label.grid(row=0, column=0, pady=5, padx=5, sticky='w')
        TaskButton(self, text='Add', command=self.add).grid(row=0, column=2, pady=5, padx=5, sticky='e')
        self.addfield = tk.Entry(self, width=20)
        self.addfield.grid(row=0, column=1, sticky='ew')
        self.addfield.focus_set()
        self.addfield.bind('<Return>', lambda event: self.add())

    def tags_update(self):
        """Создание списка тегов."""
        if hasattr(self, 'tags'):
            self.tags.destroy()
        self.tags_get()
        self.tags.grid(row=1, column=0, columnspan=3, sticky='news')
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def add(self):
        """Добавление тега в БД."""
        tagname = self.addfield.get()
        if len(tagname) > 0:
            try:
                self.add_record(tagname)
            except core.DbErrors:
                pass
            else:
                self.tags_update()

    def delete(self):
        """Удаление отмеченных тегов из БД."""
        dellist = []
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                dellist.append(item[0])
        if len(dellist) > 0:
            answer = askyesno("Really delete?", "Are you sure you want to delete selected items?")
            if answer:
                self.del_record(dellist)
                self.tags_update()

    def tags_get(self):
        self.tags = Tagslist(self.db.simple_tagslist(), self)

    def add_record(self, tagname):
        self.db.insert('tagnames', ('tag_id', 'tag_name'), (None, tagname))

    def del_record(self, dellist):
        self.db.delete(tuple(dellist), field='tag_id', table='tagnames')


class TimestampsWindow(TagsEditWindow):
    """Окно со списком таймстемпов для указанной задачи."""
    def __init__(self, taskid, current_task_time, parent=None, **options):
        self.taskid = taskid
        self.current_time = current_task_time
        super().__init__(parent=parent, **options)

    def window_elements_config(self):
        """Настройка параметров окна."""
        self.title("Timestamps")
        self.minsize(width=200, height=170)
        self.tags.canvbox.config(width=400)

    def addentry(self): pass

    def tags_get(self):
        self.tags = Tagslist(self.db.timestamps(self.taskid, self.current_time), self)

    def del_record(self, dellist):
        for x in dellist:
            self.db.exec_script('delete from timestamps where timestamp={0} and task_id={1}'.format(x, self.taskid))


class HelpWindow(tk.Toplevel):
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        main_frame=tk.Frame(self)
        self.helptext = tk.Text(main_frame, wrap='word')
        scroll = tk.Scrollbar(main_frame, command=self.helptext.yview)
        self.helptext.config(yscrollcommand=scroll.set)
        self.helptext.insert(1.0, core.HELP_TEXT)
        self.helptext.config(state='disabled')
        scroll.grid(row=0, column=1, sticky='ns')
        self.helptext.grid(row=0, column=0, sticky='news')
        main_frame.grid(row=0, column=0, sticky='news', padx=5,pady=5)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        TaskButton(self, text='ОК', command=self.destroy).grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

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


class ScrolledCanvas(tk.Frame):
    """Прокручиваемый Canvas."""
    def __init__(self, parent=None, orientation="vertical", **options):
        super().__init__(master=parent, relief='groove', bd=2, **options)
        scroller = tk.Scrollbar(self, orient=orientation)
        self.canvbox = tk.Canvas(self, width=(300 if orientation == "horizontal" else 200),
                              height=(30 if orientation == "horizontal" else 200))
        scroller.config(command=(self.canvbox.xview if orientation == "horizontal" else self.canvbox.yview))
        if orientation == "horizontal":
            self.canvbox.config(xscrollcommand=scroller.set)
        else:
            self.canvbox.config(yscrollcommand=scroller.set)
        scroller.pack(fill='x' if orientation == 'horizontal' else 'y', expand=1,
                      side='bottom' if orientation == 'horizontal' else 'right',
                      anchor='s' if orientation == 'horizontal' else 'e')
        self.content_frame = tk.Frame(self.canvbox)
        self.canvbox.create_window((0,0), window=self.content_frame, anchor='nw')
        self.content_frame.bind("<Configure>", lambda event: self.reconf_canvas())
        self.canvbox.pack(fill="x" if orientation == "horizontal" else "both", expand=1)

    def reconf_canvas(self):
        """Изменение размера области прокрутки Canvas."""
        self.canvbox.configure(scrollregion=self.canvbox.bbox('all'))


class Tagslist(ScrolledCanvas):
    """Список тегов. Формируется из списка tagslist.
    Он имеет вид [[tag_id, [state, 'tagname']]], где state может быть 0 или 1."""
    def __init__(self, tagslist, parent=None, orientation="vertical", **options):
        super().__init__(parent=parent, orientation=orientation, **options)
        self.states_list = tagslist    # Словарь id тегов с состояниями для данной таски и именами.
        for item in self.states_list:
            state = item[1][0]    # Сохраняем состояние, заданное для данного тега в словаре.
            item[1][0] = tk.IntVar()  # Подставляем вместо этого состояния динамическую переменную.
            # Добавляем к набору выключателей ещё один и связываем его с динамической переменной:
            cb = tk.Checkbutton(self.content_frame, text=item[1][1], variable=item[1][0])
            cb.pack(side=('left' if orientation == "horizontal" else 'bottom'), anchor='w')
            item[1][0].set(state)     # Передаём динамической переменной сохранённое ранее состояние.


class FilterWindow(tk.Toplevel, Db_operations):
    """Окно настройки фильтра."""
    def __init__(self, parent=None, **options):
        tk.Toplevel.__init__(self, master=parent, **options)
        Db_operations.__init__(self)
        # Списки сохранённых состояний фильтров:
        stored_dates = self.db.find_by_clause('options', 'option_name', 'filter_dates', 'value')[0][0].split(',')
        stored_tags = self.db.find_by_clause('options', 'option_name', 'filter_tags', 'value')[0][0].split(',')
        if len(stored_tags[0]) > 0:
            stored_tags = [int(x) for x in stored_tags]
        self.db.exec_script('select distinct date from dates order by date desc')
        dates = [x[0] for x in self.db.cur.fetchall()]      # Список дат.
        tags = self.db.simple_tagslist()        # Список тегов.
        for tag in tags:        # Помечаем выбранные ранее теги согласно взятой из БД информации.
            if tag[0] in stored_tags:
                tag[1][0] = 1
        tk.Label(self, text="Dates").grid(row=0, column=0, sticky='n')
        tk.Label(self, text="Tags").grid(row=0, column=1, sticky='n')
        self.dateslist = Tagslist([[x, [1 if x in stored_dates else 0, x]] for x in dates], self)
        self.tagslist = Tagslist(tags, self)
        self.dateslist.grid(row=1, column=0, pady=5, padx=5, sticky='news')
        self.tagslist.grid(row=1, column=1, pady=5, padx=5, sticky='news')
        TaskButton(self, text="Clear", command=self.clear_dates).grid(row=2, column=0, pady=7, padx=5, sticky='n')
        TaskButton(self, text="Clear", command=self.clear_tags).grid(row=2, column=1, pady=7, padx=5, sticky='n')
        tk.Frame(self, height=40).grid(row=3, column=0, columnspan=2, sticky='news')
        TaskButton(self, text="Cancel", command=self.destroy).grid(row=4, column=1, pady=5, padx=5, sticky='e')
        TaskButton(self, text='Ok', command=self.apply_filter).grid(row=4, column=0, pady=5, padx=5, sticky='w')
        self.minsize(height=250, width=250)
        self.grid_columnconfigure('all', weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.wait_window()

    def clear_dates(self):
        for x in self.dateslist.states_list:
            x[1][0].set(0)

    def clear_tags(self):
        for x in self.tagslist.states_list:
            x[1][0].set(0)

    def apply_filter(self):
        """Функция берёт фильтр из параметров, заданных в окне фильтров."""
        dates = list(reversed([x[0] for x in self.dateslist.states_list if x[1][0].get() == 1]))
        tags = list(reversed([x[0] for x in self.tagslist.states_list if x[1][0].get() == 1]))
        if len(dates) == 0 and len(tags) == 0:
            script = None
        else:
            if len(dates) > 0 and len(tags) > 0:
                script = "select distinct taskstable.* from tasks as taskstable join tags as tagstable on taskstable.id = tagstable.task_id " \
                        "join dates as datestable on taskstable.id = datestable.task_id where tagstable.tag_id in {0} "\
                        "and datestable.date in {1}".format(tuple(tags) if len(tags) > 1 else "(%s)" % tags[0],
                                                            tuple(dates) if len(dates) > 1 else "('%s')" % dates[0])
            elif len(dates) == 0:
                script = "select distinct taskstable.* from tasks as taskstable join tags as tagstable on taskstable.id = tagstable.task_id " \
                        "where tagstable.tag_id in {0}".format(tuple(tags) if len(tags) > 1 else "(%s)" % tags[0])
            elif len(tags) == 0:
                script = "select distinct taskstable.* from tasks as taskstable join dates as datestable on taskstable.id = "\
                        "datestable.task_id where datestable.date in {0}".format(tuple(dates) if len(dates) > 1 else "('%s')" % dates[0])
        self.db.update('filter', field='value', value=script, table='options', updfiled='option_name')
        self.db.update('filter_tags', field='value', value=','.join([str(x) for x in tags]), table='options', updfiled='option_name')
        self.db.update('filter_dates', field='value', value=','.join(dates), table='options', updfiled='option_name')
        self.destroy()


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


# ToDo: Хоткеи копипаста должны работать в любой раскладке. Проверить на Винде.
# ToDo: ?Сделать кнопку Clear all на главном экране.



