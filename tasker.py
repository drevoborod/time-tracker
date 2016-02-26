#!/usr/bin/env python3

import time
import db
import tkinter.font as fonter
from tkinter import *


class TaskFrame(Frame):
    """Класс отвечает за создание рамки таски со всеми элементами."""
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        self.pack()
        self.create_content()

    def create_content(self):
        """Создаёт содержимое окна и выполняет всю подготовительную работу."""
        # Создаём фейковое имя запущенной таски:
        self.task_name = None
        frame1 = Frame(self)
        frame1.pack()
        # В этом поле будет название задачи.
        self.tasklabel = TaskLabel(frame1, anchor=W, width=80)
        # Кнопка открытия списка задач.
        self.openbutton = TaskButton(frame1, "Task...", RIGHT, command=self.name_dialogue)
        frame2 = Frame(self)
        frame2.pack()
        # Кнопка "Старт"
        self.startbutton = TaskButton(frame2, "Start", LEFT, state=DISABLED, command=self.startstopbutton)
        # Начальное значения счётчика времени, потраченного на задачу.
        self.start_time = 0
        # Промежуточное значение счётчика.
        self.running_time = 0
        # Признак того, что счётчик работает.
        self.running = False
        # Окошко счётчика.
        self.timer_window = TaskLabel(frame2, width=10, state=DISABLED)
        big_font(self.timer_window)
        self.clearbutton = TaskButton(frame2, "Clear", RIGHT, state=DISABLED, command=self.clear)
        # Кнопка "Стоп".
        self.properties = TaskButton(frame2, "Properties", RIGHT, state=DISABLED, command=self.properties_window)

    def startstopbutton(self):
        """Изменяет состояние кнопки "Start/Stop". """
        if self.running:
            self.startbutton.config(text="Start")
            self.timer_stop()
        else:
            self.startbutton.config(text="Stop")
            self.timer_start()

    def properties_window(self):
        """Окно редактирования свойств таски."""
        self.timer_stop()
        self.editwindow = TaskEditWindow((self.task_name, database("one", self.task_name),
                            database("one", self.task_name, field="extra")), self)    # Берём все данные о задаче.

    def clear(self):
        """Пересоздание содержимого окна."""
        for w in self.winfo_children():
            w.destroy()
        Params.tasks.remove(self.task_name)
        self.timer_stop()
        self.create_content()

    def name_dialogue(self):
        """ Диалоговое окно выбора задачи.
        """
        self.dialogue_window = TaskSelectionWindow(self)
        Button(self.dialogue_window, text="Select", command=self.get_task_name).pack(side=LEFT)
        Button(self.dialogue_window, text="Cancel", command=self.dialogue_window.destroy).pack(side=RIGHT)

    def get_task_name(self):
        """Функция для получения имени задачи."""
        self.dialogue_window.get_selection()
        if len(self.dialogue_window.selection) == 1:
            task_name = self.dialogue_window.selection[0]
            # Пытаемся вытащить значение счётчика для данной задачи из БД.
            db_time = database("one", task_name)
            # Если задача в базе есть, то проверяем, не открыта ли она уже в другом окне:
            if task_name not in Params.tasks:
                # Проверяем, не было ли запущено уже что-то в этом окне. Если было, удаляем из списка запущенных:
                if self.task_name:
                    Params.tasks.remove(self.task_name)
                    # Останавливаем таймер старой задачи и сохраняем состояние:
                    self.timer_stop()
                    self.startbutton.config(text='Start')
                # Создаём новую задачу:
                self.prepare_task(task_name, db_time)
            else:
                # Если обнаруживаем эту задачу уже запущенной, просто закрываем окно:
                self.dialogue_window.destroy()

    def prepare_task(self, taskname, running_time=0):
        """Функция подготавливает счётчик к работе с новой таской."""
        # Добавляем имя задачи к списку запущенных:
        Params.tasks.add(taskname)
        self.task_name = taskname
        # сбрасываем текущее значение счётчика (на случай, если перед этой была открыта другая задача и счётчик уже что-то для неё показал).
        # Или задаём его значение согласно взятому из БД:
        self.running_time = running_time
        # Прописываем значение счётчика в окошке счётчика.
        self.timer_window.config(text=time_format(self.running_time))
        self.dialogue_window.destroy()
        # В поле для имени задачи прописываем имя.
        self.tasklabel.config(text=self.task_name)
        self.startbutton.config(state=NORMAL)
        self.properties.config(state=NORMAL)
        self.clearbutton.config(state=NORMAL)
        self.timer_window.config(state=NORMAL)

    def timer_update(self):
        """Обновление окошка счётчика. Обновляется раз в полсекунды."""
        self.running_time = time.time() - self.start_time
        # Собственно изменение надписи в окошке счётчика.
        self.timer_window.config(text=time_format(self.running_time))
        # Откладываем действие на полсекунды.
        # В переменную self.timer пишется ID, создаваемое методом after().
        self.timer = self.timer_window.after(500, self.timer_update)

    def timer_start(self):
        """Запуск таймера."""
        if not self.running:
            # Вытаскиваем время из БД - на тот случай, если в ней уже успело обновиться значение.
            self.start_time = time.time() - database("one", self.task_name)
            self.timer_update()
            self.running = True

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

    def destroy(self):
        """Переопределяем функцию закрытия фрейма, чтобы состояние таймера записывалось в БД."""
        self.timer_stop()
        Frame.destroy(self)


class TaskLabel(Label):
    """Простая текстовая метка для отображения значений. Визуально углублённая."""
    def __init__(self, parent, position=LEFT, **kwargs):
        Label.__init__(self, master=parent, relief=SUNKEN, **kwargs)
        self.pack(side=position)

class TaskButton(Button):
    """Просто кнопка."""
    def __init__(self, parent, text, position, **kwargs):
        Button.__init__(self, master=parent, text=text, **kwargs)
        self.pack(side=position)

class TaskList(Frame):
    """Таблица задач со скроллом."""
    def __init__(self, parent=None, **options):
        Frame.__init__(self, master=parent, **options)
        self.taskslist = Listbox(self, selectmode=EXTENDED)     # Таблица с включённым режимом множественного выделения по Control/Shift
        scroller = Scrollbar(self)
        scroller.config(command=self.taskslist.yview)           # Привязываем скролл к таблице.
        self.taskslist.config(yscrollcommand=scroller.set)      # Привязываем таблицу к скроллу :)
        scroller.pack(side=RIGHT, fill=Y)                       # Сначала нужно ставить скролл!
        self.taskslist.pack(fill=BOTH, expand=YES)              # Таблица - расширяемая во всех направлениях.


class TaskSelectionWindow(Toplevel):
    """Окно выбора и добавления задачи."""
    def __init__(self, parent=None, **options):
        Toplevel.__init__(self, master=parent, **options)
        self.title("Task selection")
        self.minsize(width=600, height=550)         # Минимальный размер окна.
        self.grab_set()                             # Остальные окна блокируются на время открытия этого.
        addframe = Frame(self)
        addframe.pack(expand=YES, fill=BOTH)
        Label(addframe, text="Enter taskname:").pack(side=LEFT)
        self.addentry = Entry(addframe)             # Поле для ввода имени новой задачи.
        self.addentry.pack(side=LEFT, expand=YES, fill=X)
        self.addbutton = Button(addframe, text="Add task", command=self.add_new_task)   # Кнопка добавления новой задачи.
        self.addbutton.pack(side=RIGHT)
        taskframe = Frame(self)
        self.listframe = TaskList(taskframe)     # Таблица тасок со скроллом.
        self.selbutton = Button(taskframe, text="Select all", command=self.select_all)
        self.delbutton = Button(taskframe, text="Remove", command=self.delete)
        self.clearbutton = Button(taskframe, text="Clear selection", command=self.clear_all)
        self.editbutton = Button(taskframe, text="Properties", command=self.edit)
        self.listframe.pack(fill=BOTH, expand=YES)
        taskframe.pack(fill=BOTH, expand=YES)
        self.selbutton.pack(side=LEFT)
        self.clearbutton.pack(side=LEFT)
        Frame(taskframe, width=300).pack()
        self.delbutton.pack(side=RIGHT)
        self.editbutton.pack(side=RIGHT)
        Frame(taskframe, height=100).pack()
        self.update_list()

    def add_new_task(self):
        """Добавление новой задачи в БД."""
        task_name = self.addentry.get()
        if len(task_name) > 0:
            if database("one", task_name) is None:  # проверяем, есть ли такая задача.
                database("add", task_name)
                self.update_list()

    def update_list(self):
        """Обновление содержимого таблицы задач (перечитываем из БД)."""
        self.listframe.taskslist.delete(0, END)     # Сначала удаяем из таблицы всё.
        self.tlist = database("all")
        for t in self.tlist:                        # А потом добавляем пункты по одному:
            self.listframe.taskslist.insert(END, t[0])

    def get_selection(self):
        """Получить список выбранных пользователем пунктов таблицы. Возвращает список названий пунктов."""
        index = [int(x) for x in self.listframe.taskslist.curselection()]   # Сначала получаем список ИНДЕКСОВ выбранных позиций.
        self.selection = [self.listframe.taskslist.get(x) for x in index]   # А потом на основании этого индекса получаем уже список имён.
        return index

    def select_all(self):
        pass

    def clear_all(self):
        pass

    def delete(self):
        """Удаление задачи из БД (и из таблицы одновременно)."""
        names = self.get_selection()
        for task in self.selection:
            database("del", task)
        for name in names:
            self.listframe.taskslist.delete(name)

    def edit(self):
        """Окно редактирования свойств таски."""
        index = self.listframe.taskslist.curselection()     # Получаем кортеж ИНДЕКСОВ выбранного пользователем.
        if len(index) > 0:
            TaskEditWindow(self.tlist[index[0]], self)    # Берём первый пункт из выбранных, остальные игнорим :)
            self.update_list()


class TaskEditWindow(Toplevel):
    """Окно редактирования свойств задачи."""
    def __init__(self, task, parent=None, **options):
        Toplevel.__init__(self, master=parent, **options)
        self.grab_set()         # Делает все остальные окна неактивными.
        self.title("Task properties")
        self.minsize(width=500, height=400)
        Label(self, text="Task name:").pack()
        self.taskname = Text(self, wrap=WORD, width=80, height=2)
        self.taskname.insert(1.0, task[0])
        self.taskname.pack()
        self.taskname.config(state=DISABLED)
        Label(self, height=5).pack()
        Label(self, text="Description:").pack()
        self.description = Text(self, width=80, height=6)
        if task[2] is not None:
            self.description.insert(1.0, task[2])
        self.description.pack()
        Label(self, height=5).pack()
        Label(self, text='Time spent:').pack(side=LEFT)
        TaskLabel(self, position=RIGHT, text='{}'.format(time_format(task[1])))
        Label(self, height=5).pack()
        Button(self, text='Ok', command=self.update_task).pack(side=LEFT)   # При нажатии на эту кнопку происходит обновление данных в БД.
        Button(self, text='Cancel', command=self.destroy).pack(side=RIGHT)
        self.wait_window()      # Ожидание закрытия этого окна, в течении которого в родителе не выполняются команды.

    def update_task(self):
        """Обновление параметров таски в БД. Пока обновляет только поле 'extra'."""
        taskdata = (self.taskname.get(1.0, END).rstrip(), self.description.get(1.0, END).rstrip())    # Имя (id) и описание задачи.
        database("update", taskdata[0], field='extra', value=taskdata[1])
        self.destroy()


class Params:
    """Пустой класс, нужный для того, чтобы использовать в качестве хранилища переменных."""
    pass


def time_format(sec):
    """Функция возвращает время в удобочитаемом формате. Принимает секунды."""
    if sec < 86400:
        return time.strftime("%H:%M:%S", time.gmtime(sec))
    else:
        return time.strftime("%jd:%H:%M:%S", time.gmtime(sec))

def big_font(unit, size=20):
    """Увеличение размера шрифта выбранного элемента до 20."""
    fontname = fonter.Font(font=unit['font']).actual()['family']
    unit.config(font=(fontname, size))

def database(action, *args, **kwargs):
    """Манипуляции с БД в зависимости от значения текстового аргумента action."""
    base = db.Db()
    result = None
    if action == "add":
        base.add_record(*args, **kwargs)
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

Params.tasks = set()    # Глобальный набор запущенных тасок. Для защиты от дублирования.
run = Tk()
run.title("Tasker")
run.resizable(width=FALSE, height=FALSE)
TaskFrame(parent=run)
TaskFrame(parent=run)
TaskFrame(parent=run)
run.mainloop()


# TODo: Сделать работоспособными кнопки "Выделить всё" и "Снять выделение".
# ToDO: Сделать диалоговое окно с предупреждением об удалении.
# ToDo: Привести в порядок внешний вид, включая корректное поведение при ресайзе.
# ToDo: Предотвращать передачу фокуса в основное окно после того, как закрыто окно редактирования свойств таски.


