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
        # Инициализируем механиз работы с БД.
        self.db_act = db.Db()
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
        self.startbutton = TaskButton(frame2, "Start", LEFT, state=DISABLED, command=self.timer_start)
        # Начальное значения счётчика времени, потраченного на задачу.
        self.start_time = 0
        # Промежуточное значение счётчика.
        self.running_time = 0
        # Признак того, что счётчик работает.
        self.running = False
        # Окошко счётчика.
        self.timer_window = TaskLabel(frame2, width=10, state=DISABLED)
        self.big_font(self.timer_window)
        self.clearbutton = TaskButton(frame2, "Clear", RIGHT, state=DISABLED, command=self.clear)
        # Кнопка "Стоп".
        self.stopbutton = TaskButton(frame2, "Stop", RIGHT, state=DISABLED, command=self.timer_stop)

    def clear(self):
        for w in self.winfo_children():
            w.destroy()
        Params.tasks.remove(self.task_name)
        self.timer_stop()
        self.db_act.close()
        self.create_content()

    def big_font(self, unit):
        """Увеличение размера шрифта выбранного элемента до 20."""
        fontname = fonter.Font(font=unit['font']).actual()['family']
        unit.config(font=(fontname, 20))

    def name_dialogue(self):
        """ Диалоговое окно выбора задачи.
        """
        self.dialogue_window = Toplevel(master=self)
        self.dialogue_window.title("Task selection")
        frame1 = Frame(self.dialogue_window)
        frame1.pack()
        tasklist = TaskList(frame1, self.tasks_list(), width=50)
        frame2 = Frame(self.dialogue_window)
        frame2.pack()
        Label(frame2, text="Enter task name:").pack()
        self.entry = Entry(frame2, width=50)
        self.entry.pack()
        self.entry.focus_set()
        TaskButton(frame2, "OK", LEFT, command=self.get_task_name)
        TaskButton(frame2, "Cancel", RIGHT, command=self.dialogue_window.destroy)

    def get_task_name(self):
        """Функция для получения имени задачи."""
        task_name = self.entry.get()
        if len(task_name) > 0:
            # Пытаемся вытащить значение счётчика для данной задачи из БД.
            db_time = self.db_act.find_record(task_name)
            # Если такая задача не обнаруживается, то создаём запись для неё
            if db_time is None:
                self.db_act.add_record(task_name)
                self.prepare_task(task_name)
            else:
                # А если задача в базе есть, то проверяем, не открыта ли она уже в другом окне:
                if task_name not in Params.tasks:
                    # Проверяем, не было ли запущено уже что-то в этом окне. Если было, удаляем из списка запущенных:
                    if self.task_name:
                        Params.tasks.remove(self.task_name)
                        # Останавливаем таймер старой задачи и сохраняем состояние:
                        self.timer_stop()
                    # Создаём новую задачу:
                    self.prepare_task(task_name, db_time[0])
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
        self.timer_window.config(text=time.strftime("%H:%M:%S", time.gmtime(self.running_time)))
        self.dialogue_window.destroy()
        # В поле для имени задачи прописываем имя.
        self.tasklabel.config(text=self.task_name)
        self.startbutton.config(state=NORMAL)
        self.stopbutton.config(state=NORMAL)
        self.clearbutton.config(state=NORMAL)
        self.timer_window.config(state=NORMAL)

    def timer_update(self):
        """Обновление окошка счётчика. Обновляется раз в полсекунды."""
        self.running_time = time.time() - self.start_time
        # Собственно изменение надписи в окошке счётчика.
        self.timer_window.config(text=time.strftime("%H:%M:%S", time.gmtime(self.running_time)))
        # Откладываем действие на полсекунды.
        # В переменную self.timer пишется ID, создаваемое методом after().
        self.timer = self.timer_window.after(500, self.timer_update)

    def timer_start(self):
        """Запуск таймера."""
        if not self.running:
            # Вытаскиваем время из БД - на тот случай, если в ней уже успело обновиться значение.
            self.start_time = time.time() - self.db_act.find_record(self.task_name)[0]
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
            self.db_act.update_record(self.task_name, value=self.running_time)

    def tasks_list(self):
        tasks = self.db_act.find_records()
        tasks_list = []
        for task in tasks:
            tasks_list.append(' '.join(map(str, task)))
        return tasks_list

    def destroy(self):
        """Переопределяем функцию закрытия фрейма, чтобы состояние таймера записывалось в БД."""
        self.timer_stop()
        self.db_act.close()
        Frame.destroy(self)


class TaskLabel(Label):
    def __init__(self, parent, **kwargs):
        Label.__init__(self, master=parent, relief=SUNKEN, **kwargs)
        self.pack(side=LEFT)

class TaskButton(Button):
    def __init__(self, parent, text, position, **kwargs):
        Button.__init__(self, master=parent, text=text, **kwargs)
        self.pack(side=position)

class TaskList(Listbox):
    def __init__(self, parent, list, position=None, **kwargs):
        Listbox.__init__(self, master=parent, **kwargs)
        for u in list:
            self.insert(END, u)
        self.pack(side=position)


class Params:
    """Пустой класс, нужный для того, чтобы использовать в качестве хранилища переменных."""
    pass

Params.tasks = set()    # Глобальный набор запущенных тасок. Для защиты от дублирования.
run = Tk()
run.title("Tasker")
TaskFrame(parent=run)
TaskFrame(parent=run)
TaskFrame(parent=run)
run.mainloop()

# TODo: В окне открытия таски сделать выбор таски из списка. Также должна быть возможность добавлять
# новые таски и удалять старые.


