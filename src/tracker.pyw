#!/usr/bin/env python3

import copy
import datetime
import os
import time
from collections import OrderedDict

try:
    import tkinter as tk
except ModuleNotFoundError:
    exit("Unable to start GUI. Please install Tk for Python:\n"
         "https://docs.python.org/3/library/tkinter.html.")

from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import askyesno, showinfo
from tkinter import ttk
from tkinter import TclError

import core
import elements
import sel_cal


class Window(tk.Toplevel):
    """Universal class for dialogue windows creation."""

    def __init__(self, master=None, **options):
        super().__init__(master=master, **options)
        self.db = core.Db()
        self.master = master
        self.bind("<Escape>", lambda e: self.destroy())

    def prepare(self):
        self.grab_set()
        self.on_top_wait()
        self.place_window(self.master)
        self.wait_window()

    def on_top_wait(self):
        """Allows window to be on the top of others
        when 'always on top' is enabled."""
        if GLOBAL_OPTIONS['always_on_top']:
            self.wm_attributes("-topmost", 1)

    def place_window(self, parent):
        """Place widget on top of parent."""
        if parent:
            stored_xpos = parent.winfo_rootx()
            self.geometry('+%d+%d' % (stored_xpos, parent.winfo_rooty()))
            self.withdraw()  # temporary hide window.
            self.update_idletasks()
            # Check if window will appear inside screen borders
            # and move it if not:
            if self.winfo_rootx() + self.winfo_width() \
                    > self.winfo_screenwidth():
                stored_xpos = (
                            self.winfo_screenwidth() - self.winfo_width() - 50)
                self.geometry('+%d+%d' % (stored_xpos, parent.winfo_rooty()))
            if self.winfo_rooty() + self.winfo_height() \
                    > self.winfo_screenheight():
                self.geometry('+%d+%d' % (stored_xpos, (
                            self.winfo_screenheight() - self.winfo_height() -
                            150)))
            self.deiconify()  # restore hidden window.

    def raise_window(self):
        self.grab_set()
        self.lift()

    def destroy(self):
        self.db.con.close()
        if self.master:
            self.master.focus_set()
            self.master.lift()
        super().destroy()


class TaskLabel(elements.SimpleLabel):
    """Simple sunken text label."""

    def __init__(self, parent, anchor='center', **kwargs):
        super().__init__(master=parent, relief='sunken', anchor=anchor,
                         **kwargs)
        context_menu = RightclickMenu()
        self.bind("<Button-3>", context_menu.context_menu_show)


class Description(tk.Frame):
    """Description frame - Text frame with scroll."""

    def __init__(self, parent=None, copy_menu=True, paste_menu=False,
                 state='normal', **options):
        super().__init__(master=parent)
        self.text = elements.SimpleText(self, bg=GLOBAL_OPTIONS["colour"],
                                        state=state, wrap='word', bd=2,
                                        **options)
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.text.yview)
        self.text.config(yscrollcommand=scroller.set)
        scroller.grid(row=0, column=1, sticky='ns')
        self.text.grid(row=0, column=0, sticky='news')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure('all', weight=1)
        # Context menu for copying contents:
        self.context_menu = RightclickMenu(copy_item=copy_menu,
                                           paste_item=paste_menu)
        self.text.bind("<Button-3>", self.context_menu.context_menu_show)
        self.text.bind("<Tab>", lambda e: self.text.tk_focusNext)

    def config(self, cnf=None, **kw):
        """Text configuration method."""
        self.text.config(cnf=cnf, **kw)

    def insert(self, text):
        self.text.insert('end', text)

    def get(self):
        return self.text.get(1.0, 'end')

    def update_text(self, text):
        """Refill text field."""
        self.config(state='normal')
        self.text.delete(1.0, 'end')
        if text is not None:
            self.text.insert(1.0, text)
        self.config(state='disabled')


class TaskFrame(tk.Frame):
    """Task frame on application's main screen."""

    def __init__(self, parent=None):
        super().__init__(master=parent, relief='raised', bd=2)
        self.db = core.Db()
        self.create_content()
        self.bind("<Button-1>", lambda e: GLOBAL_OPTIONS["selected_widget"])

    def create_content(self):
        """Creates all window elements."""
        self.startstop_var = tk.StringVar(value="Start")  # Text on "Start" button.
        # Fake name of running task (which actually is not selected yet).
        self.task = None
        if not GLOBAL_OPTIONS["compact_interface"]:
            self.normal_interface()
        # Task name field:
        self.task_label = TaskLabel(self, width=50, anchor='w')
        elements.big_font(self.task_label, size=elements.FONTSIZE + 3)
        self.task_label.grid(row=1, column=0, columnspan=5, padx=5, pady=5,
                             sticky='w')
        self.open_button = elements.TaskButton(self, text="Task...",
                                               command=self.name_dialogue)
        self.open_button.grid(row=1, column=5, padx=5, pady=5, sticky='e')
        self.start_button = elements.CanvasButton(
            self, state='disabled',
            fontsize=elements.FONTSIZE + 4,
            command=self.start_stop,
            variable=self.startstop_var,
            image=os.curdir + '/resource/start_disabled.png'
            if tk.TkVersion >= 8.6
            else os.curdir + '/resource/start_disabled.pgm',
            opacity='left')
        self.start_button.grid(row=3, column=0, sticky='wsn', padx=5)
        # Counter frame:
        self.timer_label = TaskLabel(self, width=16, state='disabled')
        elements.big_font(self.timer_label, size=elements.FONTSIZE + 8)
        self.timer_label.grid(row=3, column=1, pady=5)
        self.add_timestamp_button = elements.CanvasButton(
            self,
            text='Add\ntimestamp',
            state='disabled',
            command=self.add_timestamp
        )
        self.add_timestamp_button.grid(row=3, sticky='sn', column=2, padx=5)
        self.timestamps_window_button = elements.CanvasButton(
            self,
            text='View\ntimestamps...',
            state='disabled',
            command=self.timestamps_window
        )
        self.timestamps_window_button.grid(row=3, column=3, sticky='wsn',
                                           padx=5)
        self.properties_button = elements.TaskButton(
            self, text="Properties...", textwidth=11, state='disabled',
            command=self.properties_window)
        self.properties_button.grid(row=3, column=4, sticky='e', padx=5)
        # Clear frame button:
        self.clear_button = elements.TaskButton(self, text='Clear',
                                                state='disabled', textwidth=7,
                                                command=self.clear)
        self.clear_button.grid(row=3, column=5, sticky='e', padx=5)
        self.running = False
        self.paused = False

    def normal_interface(self):
        """Creates elements which are visible only in full interface mode."""
        # 'Task name' text:
        self.l1 = tk.Label(self, text='Task name:')
        elements.big_font(self.l1, size=elements.FONTSIZE + 2)
        self.l1.grid(row=0, column=1, columnspan=3)
        # Task description field:
        self.description_area = Description(self, width=60, height=3)
        self.description_area.grid(row=2, column=0, columnspan=6, padx=5,
                                   pady=6, sticky='we')
        if self.task:
            self.description_area.update_text(self.task['descr'])

    def small_interface(self):
        """Destroy some interface elements when switching to 'compact' mode."""
        for widget in (self.l1, self.description_area):
            widget.destroy()
        if hasattr(self, "description_area"):
            delattr(self, "description_area")

    def timestamps_window(self):
        """Timestamps window opening."""
        TimestampsWindow(self.task["id"], self.task["spent_total"],
                         ROOT_WINDOW)

    def add_timestamp(self, event_type=core.LOG_EVENTS["CUSTOM"],
                      comment=None):
        """Adding timestamp to database."""
        # Need to preserve time as it was at the moment of function calling:
        timestamp = self.task["spent_total"]
        current_time = core.date_format(datetime.datetime.now(),
                                        core.DATE_STORAGE_TEMPLATE)
        show_message = False
        if comment is None:
            apply_var = tk.BooleanVar()
            comment_var = tk.StringVar()
            TimestampCommentWindow(self, comment_var=comment_var,
                                   apply_var=apply_var)
            if apply_var.get():
                show_message = True
                comment = comment_var.get()
        if comment is not None:
            self.db.insert('timestamps',
                           ('task_id', 'timestamp', 'event_type',
                            'datetime', 'comment'),
                           (self.task["id"], timestamp, event_type,
                            current_time, comment))
        if show_message:
            showinfo("Timestamp added", "Timestamp added.")

    def start_stop(self):
        """Changes "Start/Stop" button state. """
        if self.running:
            self.timer_stop()
        else:
            self.timer_start()

    def properties_window(self):
        """Task properties window."""
        edited_var = tk.IntVar()
        TaskEditWindow(self.task["id"], parent=ROOT_WINDOW,
                       variable=edited_var)
        if edited_var.get() == 1:
            self.update_description()

    def clear(self):
        """Recreation of frame contents."""
        message = "Task frame cleared."
        self.timer_stop(log_message=message)
        if self.paused:
            self.add_timestamp(core.LOG_EVENTS["STOP"], message)
            if len(get_paused_taskframes()) == 0:
                ROOT_WINDOW.change_paused_state()
        if self.task:
            GLOBAL_OPTIONS["tasks"].pop(self.task["id"])
            if GLOBAL_OPTIONS["preserve_tasks"]:
                self.db.update_preserved_tasks(GLOBAL_OPTIONS["tasks"])
        for w in self.winfo_children():
            w.destroy()
        self.create_content()
        ROOT_WINDOW.taskframes.fill()

    def name_dialogue(self):
        """Task selection window."""
        var = tk.IntVar()
        TaskSelectionWindow(ROOT_WINDOW, taskvar=var)
        if var.get():
            self.get_task_name(var.get())

    def get_task_name(self, task_id):
        """Getting selected task's name."""
        # Checking if task is already open in another frame:
        if task_id not in GLOBAL_OPTIONS["tasks"]:
            # Checking if there is open task in this frame:
            if self.task:
                # Stopping current timer and saving its state:
                self.timer_stop()
                # If there is open task, we remove it from running tasks set:
                GLOBAL_OPTIONS["tasks"].pop(self.task["id"])
                if self.paused:
                    self.paused = False
                    self.add_timestamp(core.LOG_EVENTS["STOP"],
                                       "Another task opened in the frame.")
                    if len(get_paused_taskframes()) == 0:
                        ROOT_WINDOW.change_paused_state()
            self.get_restored_task_name(task_id)
        else:
            # If selected task is already opened in another frame:
            message = "Task exists", "Task is already opened."
            if not self.task:
                showinfo(*message)
            else:
                if self.task["id"] != task_id:
                    showinfo(*message)

    def get_restored_task_name(self, taskid):
        # Preparing new task:
        self.set_task_data(taskid)
        self.prepare_task()

    def set_task_data(self, taskid):
        """Get task data from database"""
        self.task = self.db.select_task(taskid) # Task parameters from database

    def prepare_task(self):
        """Prepares frame elements to work with."""
        self.current_date = core.today()
        # Adding task id and state to dictionary of running tasks:
        GLOBAL_OPTIONS["tasks"][self.task["id"]] = False
        self.configure_indicator()
        self.task_label.config(text=self.task["name"])
        self.start_button.config(state='normal')
        self.start_button.config(image=os.curdir + '/resource/start_normal.png'
                                 if tk.TkVersion >= 8.6
                                 else os.curdir + '/resource/start_normal.pgm')
        self.properties_button.config(state='normal')
        self.clear_button.config(state='normal')
        self.timer_label.config(state='normal')
        self.add_timestamp_button.config(state='normal')
        self.timestamps_window_button.config(state='normal')
        if hasattr(self, "description_area"):
            self.description_area.update_text(self.task["descr"])
        if GLOBAL_OPTIONS["preserve_tasks"]:
            self.db.update_preserved_tasks(GLOBAL_OPTIONS["tasks"])

    def configure_indicator(self):
        """Configure timer indicator depending on time displaying options value."""
        if self.task:
            if GLOBAL_OPTIONS["show_today"]:
                spent = self.task["spent_today"]
            else:
                spent = self.task["spent_total"]
            self.timer_label.config(text=core.time_format(spent))

    def task_update(self):
        """Updates time in the database."""
        res = self.db.update_task(self.task["id"],
                                  value=self.task["spent_today"],
                                  prev_date=self.current_date)
        if res:
            self.current_date = res.current_date
            self.task["spent_today"] = res.remained

    def timer_update(self, counter=0):
        """Renewal of the counter."""
        spent = time.time() - self.start_time
        self.task["spent_today"] += spent
        self.task["spent_total"] += spent
        self.start_time = time.time()
        self.configure_indicator()
        # Every n seconds counter value is saved in database:
        if counter >= GLOBAL_OPTIONS["SAVE_INTERVAL"]:
            self.task_update()
            counter = 0
        else:
            counter += GLOBAL_OPTIONS["TIMER_INTERVAL"]
        # self.timer variable becomes ID created by after():
        self.timer = self.timer_label.after(
            GLOBAL_OPTIONS["TIMER_INTERVAL"], self.timer_update, counter)

    def timer_start(self, log=True, stop_all=True):
        """Counter start."""
        if not self.running:
            self.start_button.config(
                image=os.curdir + '/resource/stop.png' if tk.TkVersion >= 8.6
                else os.curdir + '/resource/stop.pgm')
            self.startstop_var.set("Stop")
            was_paused = False
            if log:
                if self.paused:
                    event_id = core.LOG_EVENTS["RESUME"]
                    comment = "Task resumed."
                    was_paused = True
                else:
                    event_id = core.LOG_EVENTS["START"]
                    comment = "Task started."
                self.add_timestamp(event_id, comment)
            if GLOBAL_OPTIONS["toggle_tasks"]:
                if stop_all and not was_paused:
                    ROOT_WINDOW.stop_all()
            GLOBAL_OPTIONS["tasks"][self.task["id"]] = True
            self.current_date = core.today()
            self.set_task_data(self.task["id"])
            self.configure_indicator()
            # Setting current timestamp:
            self.start_time = time.time()
            self.running = True
            self.paused = False
            if not get_paused_taskframes():
                ROOT_WINDOW.change_paused_state()
            self.timer_update()

    def timer_stop(self, log=True, log_message=None, paused=False):
        """Stop counter and save its value to database."""
        event_id = core.LOG_EVENTS["STOP"]
        comment = "Task stopped." if not log_message else log_message
        if self.paused:
            if log:
                self.add_timestamp(event_id, comment)
        if self.running:
            # after_cancel() stops execution of callback with given ID.
            self.timer_label.after_cancel(self.timer)
            self.running = False
            GLOBAL_OPTIONS["tasks"][self.task["id"]] = False
            # Writing value into database:
            self.task_update()
            self.update_description()
            if paused:
                event_id = core.LOG_EVENTS["PAUSE"]
                comment = "Task paused."
            self.start_button.config(
                image=os.curdir + '/resource/start_normal.png'
                if tk.TkVersion >= 8.6
                else os.curdir + '/resource/start_normal.pgm')
            self.startstop_var.set("Start")
            if log:
                self.add_timestamp(event_id, comment)
        self.paused = paused

    def update_description(self):
        """Update text in "Description" field."""
        self.task["descr"] = \
        self.db.find_by_clause("tasks", "id", self.task["id"],
                               "description")[0][0]
        if hasattr(self, "description_area"):
            self.description_area.update_text(self.task["descr"])

    def destroy(self):
        """Closes frame and writes counter value into database."""
        message = "Task stopped on application exit."
        self.timer_stop(log_message=message)
        if self.paused:
            self.add_timestamp(core.LOG_EVENTS["STOP"], message)
        if self.task:
            GLOBAL_OPTIONS["tasks"].pop(self.task["id"])
        self.db.con.close()
        tk.Frame.destroy(self)


class TimestampCommentWindow(Window):
    """Task properties window."""

    def __init__(self, parent=None, comment_var=None, apply_var=None,
                 **options):
        super().__init__(master=parent, **options)
        self.comment_var = comment_var
        self.apply_var = apply_var
        self.title("Timestamp comment")
        elements.SimpleLabel(self, text="Enter comment:", fontsize=elements.FONTSIZE + 1).grid(
            row=0, column=0, columnspan=2, pady=5, padx=5, sticky='we')
        self.comment_area = elements.SimpleEntry(self)
        self.comment_area.config(state='normal', bg='white')
        self.comment_area.grid(row=1, column=0, columnspan=2, sticky='we')

        tk.Frame(self, height=40).grid(row=2)
        elements.TaskButton(self, text='Ok', command=self.get_comment).grid(
            row=3, column=0, sticky='sw', padx=5, pady=5)
        elements.TaskButton(self, text='Cancel', command=self.destroy).grid(
            row=3, column=1, sticky='se', padx=5, pady=5)
        context_menu = RightclickMenu(paste_item=1, copy_item=0)
        self.comment_area.bind("<Button-3>", context_menu.context_menu_show)
        self.comment_area.bind("<Return>", lambda e: self.get_comment())
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.resizable(height=0, width=1)
        self.minsize(width=500, height=10)
        self.comment_area.focus_set()
        self.prepare()

    def get_comment(self):
        self.apply_var.set(True)
        self.comment_var.set(self.comment_area.get())
        self.destroy()


class Table(tk.Frame):

    def __init__(self, columns, parent=None, **options):
        super().__init__(master=parent, **options)
        self.table = ttk.Treeview(self)
        style = ttk.Style()
        style.configure(".", font=('Helvetica', elements.FONTSIZE + 1))
        style.configure("Treeview.Heading", font=('Helvetica', elements.FONTSIZE + 1))
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.table.yview)
        self.table.config(yscrollcommand=scroller.set)
        scroller.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=1)
        # Creating and naming columns:
        self.table.config(columns=tuple([key for key in columns]))
        for name in columns:
            # Configuring columns with given ids:
            self.table.column(name, width=100, minwidth=100,
                              anchor='center')
            # Configuring headers of columns with given ids:
            self.table.heading(name, text=columns[name],
                               command=lambda c=name:
                                        self.sort_table_contents(c, True))
        self.table.column('#0', anchor='w', width=70, minwidth=50,
                          stretch=0)

    def _sort(self, position, reverse):
        l = []
        for index, task in enumerate(self.table.get_children()):
            l.append((self.data[index][position], task))
        # Sort tasks list by corresponding field to match current sorting:
        self.data.sort(key=lambda x: x[position], reverse=reverse)
        return l

    def sort_table_contents(self, col, reverse):
        """Should be redefined by successors."""
        pass

    def focus_(self, item):
        """Focuses on the row with provided id."""
        self.table.see(item)
        self.table.selection_set(item)
        self.table.focus_set()
        self.table.focus(item)

    def update_data(self, data):
        """Update contents of internal data used to fill the table."""
        for item in self.table.get_children():
            self.table.delete(item)
        self.data = copy.deepcopy(data)

    def insert_rows(self, data):
        """Insert rows in the table. Row contents
        are tuples provided by 'values='."""
        for i, v in enumerate(data):  # item, number, value:
            self.table.insert('', i, text="#%d" % (i + 1), values=v)

    def select_all(self):
        self.table.selection_set(
            self.table.get_children())

    def clear_all(self):
        self.table.selection_remove(
            self.table.get_children())


class TaskTable(Table):
    """Scrollable tasks table."""

    def __init__(self, columns, parent=None, **options):
        super().__init__(columns, parent=parent, **options)
        self.table.column('taskname', width=600, anchor='w')

    def sort_table_contents(self, col, reverse):
        """Sorting by click on column header."""
        if col == "spent_time":
            shortlist = self._sort(1, reverse)
        elif col == "creation_date":
            shortlist = self._sort(2, reverse)
        else:
            shortlist = self._sort(0, reverse)
        shortlist.sort(key=lambda x: x[0], reverse=reverse)
        for index, value in enumerate(shortlist):
            self.table.move(value[1], '', index)
        self.table.heading(col, command=lambda:
                                    self.sort_table_contents(col, not reverse))

    def update_tasks_list(self, data):
        """Refill table contents."""
        self.update_data(data)
        for t in data:
            t[1] = core.time_format(t[1])
            t[2] = core.table_date_format(t[2])
        self.insert_rows(data)


class TaskSelectionWindow(Window):
    """Task selection and creation window."""

    def __init__(self, parent=None, taskvar=None, **options):
        super().__init__(master=parent, **options)
        # Variable which will contain selected task id:
        if taskvar:
            self.task_id_var = taskvar
        # Basic script for retrieving tasks from database:
        self.main_script = 'SELECT id, name, total_time, description, ' \
                           'creation_date FROM tasks JOIN (SELECT task_id, ' \
                           'sum(spent_time) AS total_time FROM activity ' \
                           'GROUP BY task_id) AS act ON act.task_id=tasks.id'
        self.title("Task selection")
        self.minsize(width=500, height=350)
        elements.SimpleLabel(self, text="New task:").grid(row=0, column=0,
                                                          sticky='w', pady=5,
                                                          padx=5)
        # New task entry field:
        self.add_entry = elements.SimpleEntry(self, width=50)
        self.add_entry.grid(row=0, column=1, columnspan=3, sticky='we')
        # Enter adds new task:
        self.add_entry.bind('<Return>', lambda event: self.add_new_task())
        self.add_entry.focus_set()
        # Context menu with 'Paste' option:
        addentry_context_menu = RightclickMenu(paste_item=1, copy_item=0)
        self.add_entry.bind("<Button-3>",
                            addentry_context_menu.context_menu_show)
        # "Add task" button:
        self.add_button = elements.TaskButton(self, text="Add task",
                                              command=self.add_new_task,
                                              takefocus=False)
        self.add_button.grid(row=0, column=4, sticky='e', padx=6, pady=5)
        # Entry for typing search requests:
        self.search_entry = elements.SimpleEntry(self, width=25)
        self.search_entry.grid(row=1, column=1, columnspan=2, sticky='we',
                               padx=5, pady=5)
        searchentry_context_menu = RightclickMenu(paste_item=1, copy_item=0)
        self.search_entry.bind("<Button-3>",
                               searchentry_context_menu.context_menu_show)
        # Case sensitive checkbutton:
        self.ignore_case_var = tk.IntVar(self, value=1)
        elements.SimpleCheckbutton(self, text="Ignore case", takefocus=False,
                                   variable=self.ignore_case_var).grid(row=1,
                                                                       column=0,
                                                                       padx=6,
                                                                       pady=5,
                                                                       sticky='w')
        # Search button:
        elements.CanvasButton(self, takefocus=False, text='Search',
                              image=os.curdir + '/resource/magnifier.png'
                              if tk.TkVersion >= 8.6
                              else os.curdir + '/resource/magnifier.pgm',
                              command=self.locate_task).grid(row=1, column=3,
                                                             sticky='w',
                                                             padx=5, pady=5)
        # Refresh button:
        elements.TaskButton(self, takefocus=False,
                            image=os.curdir + '/resource/refresh.png'
                            if tk.TkVersion >= 8.6
                            else os.curdir + '/resource/refresh.pgm',
                            command=self.update_table).grid(row=1, column=4,
                                                            sticky='e', padx=5,
                                                            pady=5)
        # Naming of columns in tasks list:
        column_names = OrderedDict({'taskname': 'Task name',
                                    'spent_time': 'Spent time',
                                    'creation_date': 'Created'})
        # Scrollable tasks table:
        self.table_frame = TaskTable(column_names, self, takefocus=True)
        self.table_frame.grid(row=2, column=0, columnspan=5, pady=10,
                              sticky='news')
        elements.SimpleLabel(self, text="Summary time:").grid(row=3, column=0,
                                                              pady=5, padx=5,
                                                              sticky='w')
        # Summarized time of all tasks in the table:
        self.fulltime_frame = TaskLabel(self, width=16, anchor='center')
        self.fulltime_frame.grid(row=3, column=1, padx=6, pady=5, sticky='e')
        # Selected task description:
        self.description_area = Description(self, height=4)
        self.description_area.grid(row=3, column=2, rowspan=2, pady=5, padx=5,
                                   sticky='news')
        # "Select all" button:
        sel_button = elements.TaskButton(self, text="Select all",
                                         command=self.table_frame.select_all)
        sel_button.grid(row=4, column=0, sticky='w', padx=5, pady=5)
        # "Clear all" button:
        clear_button = elements.TaskButton(self, text="Clear selection",
                                           textwidth=12,
                                           command=self.table_frame.clear_all)
        clear_button.grid(row=4, column=1, sticky='e', padx=5, pady=5)
        # Task properties button:
        self.edit_button = elements.TaskButton(self, text="Properties...",
                                               textwidth=10, command=self.edit)
        self.edit_button.grid(row=3, column=3, sticky='w', padx=5, pady=5)
        # Remove task button:
        self.del_button = elements.TaskButton(self, text="Remove...",
                                              textwidth=10, command=self.delete)
        self.del_button.grid(row=4, column=3, sticky='w', padx=5, pady=5)
        # Export button:
        self.export_button = elements.TaskButton(self, text="Export...",
                                                 command=self.export)
        self.export_button.grid(row=4, column=4, padx=5, pady=5, sticky='e')
        # Filter button:
        self.filter_button = elements.TaskButton(self, text="Filter...",
                                                 command=self.filterwindow)
        self.filter_button.grid(row=3, column=4, padx=5, pady=5, sticky='e')
        # Filter button context menu:
        filter_context_menu = RightclickMenu(copy_item=False)
        filter_context_menu.add_command(label='Clear filter',
                                        command=self.apply_filter)
        self.filter_button.bind("<Button-3>",
                                filter_context_menu.context_menu_show)
        tk.Frame(self, height=40).grid(row=5, columnspan=5, sticky='news')
        self.grid_columnconfigure(2, weight=1, minsize=50)
        self.grid_rowconfigure(2, weight=1, minsize=50)
        self.update_table()  # Fill table contents.
        self.current_task = ''  # Current selected task.
        self.table_frame.table.bind("<Down>", self.descr_down)
        self.table_frame.table.bind("<Up>", self.descr_up)
        self.table_frame.table.bind("<Button-1>", self.descr_click)
        self.table_frame.bind("<FocusIn>",
                              lambda e: self.focus_first_item(forced=False))
        # Need to avoid masquerading of default ttk.Treeview action
        # on Shift+click and Control+click:
        self.modifier_pressed = False
        self.table_frame.table.bind("<KeyPress-Shift_L>",
                                    lambda e: self.shift_control_pressed())
        self.table_frame.table.bind("<KeyPress-Shift_R>",
                                    lambda e: self.shift_control_pressed())
        self.table_frame.table.bind("<KeyPress-Control_L>",
                                    lambda e: self.shift_control_pressed())
        self.table_frame.table.bind("<KeyPress-Control_R>",
                                    lambda e: self.shift_control_pressed())
        self.table_frame.table.bind("<KeyRelease-Shift_L>",
                                    lambda e: self.shift_control_released())
        self.table_frame.table.bind("<KeyRelease-Shift_R>",
                                    lambda e: self.shift_control_released())
        self.table_frame.table.bind("<KeyRelease-Control_L>",
                                    lambda e: self.shift_control_released())
        self.table_frame.table.bind("<KeyRelease-Control_R>",
                                    lambda e: self.shift_control_released())
        self.search_entry.bind("<Return>", lambda e: self.locate_task())
        self.bind("<F5>", lambda e: self.update_table())
        elements.TaskButton(self, text="Open", command=self.get_task).grid(
            row=6, column=0, padx=5, pady=5, sticky='w')
        elements.TaskButton(self, text="Cancel", command=self.destroy).grid(
            row=6, column=4, padx=5, pady=5, sticky='e')
        self.table_frame.table.bind("<Return>", self.get_task_id)
        self.table_frame.table.bind("<Double-1>", self.get_task_id)
        self.prepare()

    def check_row(self, event):
        """Check if mouse click is over the row,
        not another tasks_table element."""
        if (event.type == '4' and len(
                self.table_frame.table.identify_row(event.y)) > 0) or (
                event.type == '2'):
            return True

    def get_task(self):
        """Get selected task id from database and close window."""
        # List of selected tasks item id's:
        tasks = self.table_frame.table.selection()
        if tasks:
            self.task_id_var.set(self.tdict[tasks[0]]["id"])
            self.destroy()

    def get_task_id(self, event):
        """For clicking on buttons and items."""
        if self.check_row(event):
            self.get_task()

    def shift_control_pressed(self):
        self.modifier_pressed = True

    def shift_control_released(self):
        self.modifier_pressed = False

    def focus_first_item(self, forced=True):
        """Selects first item in the table if no items selected."""
        if self.table_frame.table.get_children():
            item = self.table_frame.table.get_children()[0]
        else:
            return
        if forced:
            self.table_frame.focus_(item)
            self.update_descr(item)
        else:
            if not self.table_frame.table.selection():
                self.table_frame.focus_(item)
                self.update_descr(item)
            else:
                self.table_frame.table.focus_set()

    def locate_task(self):
        """Search task by keywords."""
        searchword = self.search_entry.get()
        if searchword:
            self.table_frame.clear_all()
            task_items = []
            if self.ignore_case_var.get():
                for key in self.tdict:
                    if searchword.lower() in self.tdict[key]["name"].lower():
                        task_items.append(key)
                    # Need to be sure that there is non-empty description:
                    elif self.tdict[key]["descr"]:
                        if searchword.lower() in self.tdict[key]["descr"].lower():
                            task_items.append(key)
            else:
                for key in self.tdict:
                    if searchword in self.tdict[key]["name"]:
                        task_items.append(key)
                    elif self.tdict[key]["descr"]:
                        if searchword in self.tdict[key]["descr"]:
                            task_items.append(key)
            if task_items:
                for item in task_items:
                    self.table_frame.table.selection_add(item)
                item = self.table_frame.table.selection()[0]
                self.table_frame.table.see(item)
                self.table_frame.table.focus_set()
                self.table_frame.table.focus(item)
                self.update_descr(item)
            else:
                showinfo("No results",
                         "No tasks found."
                         "\nMaybe need to change filter settings?")

    def export(self):
        """Export all tasks from the table into the file."""
        ExportWindow(self, self.tdict)

    def add_new_task(self):
        """Adds new task into the database."""
        task_name = self.add_entry.get()
        if task_name:
            for x in ('"', "'", "`"):
                task_name = task_name.replace(x, '')
            try:
                self.db.insert_task(task_name)
            except core.DbErrors:
                self.db.reconnect()
                for item in self.tdict:
                    if self.tdict[item]["name"] == task_name:
                        self.table_frame.focus_(item)
                        self.update_descr(item)
                        break
                else:
                    showinfo("Task exists",
                             "Task already exists. "
                             "Change filter configuration to see it.")
            else:
                self.update_table()
                # If created task appears in the table, highlight it:
                for item in self.tdict:
                    if self.tdict[item]["name"] == task_name:
                        self.table_frame.focus_(item)
                        break
                else:
                    showinfo("Task created",
                             "Task successfully created. "
                             "Change filter configuration to see it.")

    def filter_query(self):
        return self.db.find_by_clause(table='options', field='name',
                                      value='filter', searchfield='value')[0][0]

    def update_table(self):
        """Updating table contents using database query."""
        # Restoring filter value:
        query = self.filter_query()
        if query:
            self.filter_button.config(bg='lightblue')
            self.db.exec_script(query)
        else:
            self.filter_button.config(bg=GLOBAL_OPTIONS["colour"])
            self.db.exec_script(self.main_script)
        tlist = [{"id": task[0], "name": task[1], "spent_time": task[2],
                  "descr": task[3], "creation_date": task[4]}
                 for task in self.db.cur.fetchall()]
        self.table_frame.update_tasks_list(
            [[f["name"], f["spent_time"], f["creation_date"]] for f in tlist])
        # Dictionary with row ids and tasks info:
        self.tdict = {}
        for n, task_id in enumerate(self.table_frame.table.get_children()):
            self.tdict[task_id] = tlist[n]
        self.update_descr(None)
        self.update_fulltime()

    def update_fulltime(self):
        """Updates value in "fulltime" frame."""
        self.fulltime = core.time_format(
            sum([self.tdict[x]["spent_time"] for x in self.tdict]))
        self.fulltime_frame.config(text=self.fulltime)

    def descr_click(self, event):
        """Updates description for the task with item id of the row
        selected by click."""
        pos = self.table_frame.table.identify_row(event.y)
        if pos and pos != '#0' and not self.modifier_pressed:
            self.table_frame.focus_(pos)
        self.update_descr(self.table_frame.table.focus())

    def descr_up(self, event):
        """Updates description for the item id which is BEFORE selected."""
        item = self.table_frame.table.focus()
        prev_item = self.table_frame.table.prev(item)
        if prev_item == '':
            self.update_descr(item)
        else:
            self.update_descr(prev_item)

    def descr_down(self, event):
        """Updates description for the item id which is AFTER selected."""
        item = self.table_frame.table.focus()
        next_item = self.table_frame.table.next(item)
        if next_item == '':
            self.update_descr(item)
        else:
            self.update_descr(next_item)

    def update_descr(self, item):
        """Filling task description frame."""
        if item is None:
            self.description_area.update_text('')
        elif item != '':
            self.description_area.update_text(self.tdict[item]["descr"])

    def delete(self):
        """Remove selected tasks from the database and the table."""
        ids = [self.tdict[x]["id"] for x in self.table_frame.table.selection()
               if self.tdict[x]["id"] not in GLOBAL_OPTIONS["tasks"]]
        items = [x for x in self.table_frame.table.selection() if
                 self.tdict[x]["id"] in ids]
        if ids:
            answer = askyesno("Warning",
                              "Are you sure you want to delete selected tasks?",
                              parent=self)
            if answer:
                self.db.delete_tasks(tuple(ids))
                self.table_frame.table.delete(*items)
                for item in items:
                    self.tdict.pop(item)
                self.update_descr(None)
                self.update_fulltime()

    def edit(self):
        """Show task edit window."""
        item = self.table_frame.table.focus()
        try:
            id_name = {"id": self.tdict[item]["id"],
                       "name": self.tdict[item]["name"]}
        except KeyError:
            pass
        else:
            task_changed = tk.IntVar()
            TaskEditWindow(id_name["id"], self, variable=task_changed)
            if task_changed.get() == 1:
                # Reload task information from database:
                new_task_info = self.db.select_task(id_name["id"])
                # Update description:
                self.tdict[item]["descr"] = new_task_info["descr"]
                self.update_descr(item)
        self.raise_window()

    def filterwindow(self):
        """Open filters window."""
        filter_changed = tk.IntVar()
        FilterWindow(self, variable=filter_changed)
        # Update tasks list only if filter parameters have been changed:
        if filter_changed.get() == 1:
            self.apply_filter(GLOBAL_OPTIONS["filter_dict"]['operating_mode'],
                              GLOBAL_OPTIONS["filter_dict"]['script'],
                              GLOBAL_OPTIONS["filter_dict"]['tags'],
                              GLOBAL_OPTIONS["filter_dict"]['dates'])
        self.raise_window()

    def apply_filter(self, operating_mode='AND', script=None, tags='',
                     dates=''):
        """Record filter parameters to database and apply it."""
        update = self.filter_query()
        self.db.update('filter_operating_mode', field='value',
                       value=operating_mode, table='options', updfield='name')
        self.db.update('filter', field='value', value=script, table='options',
                       updfield='name')
        self.db.update('filter_tags', field='value',
                       value=','.join([str(x) for x in tags]), table='options',
                       updfield='name')
        self.db.update('filter_dates', field='value', value=','.join(dates),
                       table='options', updfield='name')
        if update != self.filter_query():
            self.update_table()


class TaskEditWindow(Window):
    """Task properties window."""

    def __init__(self, taskid, parent=None, variable=None, **options):
        super().__init__(master=parent, **options)
        # Connected with external IntVar.
        # Needed to avoid unnecessary operations in parent window:
        self.change_var = variable
        # Task information from database:
        self.task = self.db.select_task(taskid)
        # List of dates connected with this task:
        dates = [x[0] + " - " + core.time_format(x[1]) for x in
                 self.db.find_by_clause('activity', 'task_id', '%s' %
                                        taskid, 'date, spent_time', 'date')]
        self.title("Task properties: {}".format(
            self.db.find_by_clause('tasks', 'id', taskid, 'name')[0][0]))
        self.minsize(width=400, height=300)
        elements.SimpleLabel(self, text="Task name:", fontsize=elements.FONTSIZE + 1).grid(
            row=0, column=0, pady=5, padx=5, sticky='w')
        # Frame containing task name:
        TaskLabel(self, width=60, height=1, bg=GLOBAL_OPTIONS["colour"],
                  text=self.task["name"],
                  anchor='w').grid(row=1, columnspan=5, sticky='ew', padx=6)
        tk.Frame(self, height=30).grid(row=2)
        elements.SimpleLabel(self, text="Description:", fontsize=elements.FONTSIZE + 1).grid(
            row=3, column=0, pady=5, padx=5, sticky='w')
        # Task description frame. Editable:
        self.description_area = Description(self, paste_menu=True, width=60,
                                            height=6)
        self.description_area.config(state='normal', bg='white')
        if self.task["descr"]:
            self.description_area.insert(self.task["descr"])
        self.description_area.grid(row=4, columnspan=5, sticky='ewns', padx=5)
        #
        elements.SimpleLabel(self, text='Tags:').grid(row=5, column=0, pady=5,
                                                      padx=5, sticky='nw')
        # Place tags list:
        self.tags_update()
        elements.TaskButton(self, text='Edit tags', textwidth=10,
                            command=self.tags_edit).grid(row=5, column=4,
                                                         padx=5, pady=5,
                                                         sticky='e')
        elements.SimpleLabel(self, text='Time spent:').grid(row=6, column=0,
                                                            padx=5, pady=5,
                                                            sticky='w')
        # Frame containing time:
        TaskLabel(self, width=16,
                  text='{}'.format(
                      core.time_format(self.task["spent_total"]))).grid(
                            row=6, column=1, pady=5, padx=5, sticky='w')
        elements.SimpleLabel(self, text='Dates:').grid(row=6, column=2,
                                                       sticky='w')
        # Frame containing list of dates connected with current task:
        date_list = Description(self, height=3, width=30)
        date_list.update_text('\n'.join(dates))
        date_list.grid(row=6, column=3, rowspan=3, columnspan=2, sticky='ew',
                     padx=5, pady=5)
        #
        tk.Frame(self, height=40).grid(row=9)
        elements.TaskButton(self, text='Ok', command=self.update_task).grid(
            row=10, column=0, sticky='sw', padx=5, pady=5)
        elements.TaskButton(self, text='Cancel', command=self.destroy).grid(
            row=10, column=4, sticky='se', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=10)
        self.grid_rowconfigure(4, weight=1)
        self.description_area.text.focus_set()
        self.prepare()

    def tags_edit(self):
        """Open tags editor window."""
        TagsEditWindow(self)
        self.tags_update()
        self.grab_set()
        self.lift()
        self.focus_set()

    def tags_update(self):
        """Tags list placing."""
        # Tags list. Tags state are saved to database:
        self.tags = Tagslist(self.db.tags_dict(self.task["id"]), self,
                             orientation='horizontal', width=300, height=30)
        self.tags.grid(row=5, column=1, columnspan=3, pady=5, padx=5,
                       sticky='we')

    def update_task(self):
        """Update task in database."""
        task_data = self.description_area.get().rstrip()
        self.db.update_task(self.task["id"], field='description',
                            value=task_data)
        # Renew tags list for the task:
        existing_tags = [x[0] for x in
                         self.db.find_by_clause('tasks_tags', 'task_id',
                                                self.task["id"], 'tag_id')]
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                if item[0] not in existing_tags:
                    self.db.insert('tasks_tags', ('task_id', 'tag_id'),
                                   (self.task["id"], item[0]))
            else:
                self.db.delete(table="tasks_tags", task_id=self.task["id"],
                               tag_id=item[0])
        # Reporting to parent window that task has been changed:
        if self.change_var:
            self.change_var.set(1)
        self.destroy()


class TagsEditWindow(Window):
    """Checkbuttons editing window."""

    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.parent = parent
        self.addentry()
        self.tags_update()
        self.close_button = elements.TaskButton(self, text='Close',
                                                command=self.destroy)
        self.delete_button = elements.TaskButton(self, text='Delete',
                                                 command=self.delete)
        self.maxsize(width=500, height=500)
        self.window_elements_config()
        self.prepare()

    def window_elements_config(self):
        """Window additional parameters configuration."""
        self.title("Tags editor")
        self.minsize(width=300, height=300)
        self.close_button.grid(row=2, column=2, pady=5, padx=5, sticky='e')
        self.delete_button.grid(row=2, column=0, pady=5, padx=5, sticky='w')

    def addentry(self):
        """New element addition field"""
        self.addentry_label = elements.SimpleLabel(self, text="Add tag:")
        self.addentry_label.grid(row=0, column=0, pady=5, padx=5, sticky='w')
        elements.TaskButton(self, text='Add', command=self.add).grid(
            row=0, column=2, pady=5, padx=5, sticky='e')
        self.addfield = elements.SimpleEntry(self, width=20)
        self.addfield.grid(row=0, column=1, sticky='ew')
        self.addfield.focus_set()
        self.addfield.bind('<Return>', lambda event: self.add())

    def tags_update(self):
        """Tags list recreation."""
        if hasattr(self, 'tags'):
            self.tags.destroy()
        self.tags_get()
        self.tags.grid(row=1, column=0, columnspan=3, sticky='news')
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def add(self):
        """Insert new element into database."""
        tagname = self.addfield.get()
        if tagname:
            try:
                self.add_record(tagname)
            except core.DbErrors:
                self.db.reconnect()
            else:
                self.tags_update()

    def delete(self):
        """Remove selected elements from database."""
        dellist = []
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                dellist.append(item[0])
        if dellist:
            answer = askyesno("Really delete?",
                              "Are you sure you want to delete selected items?",
                              parent=self)
            if answer:
                self.del_record(dellist)
                self.tags_update()

    def tags_get(self):
        self.tags = Tagslist(self.db.simple_tagslist(), self, width=300,
                             height=300)

    def add_record(self, tagname):
        self.db.insert('tags', ('id', 'name'), (None, tagname))

    def del_record(self, dellist):
        self.db.delete(id=dellist, table='tags')
        self.db.delete(tag_id=dellist, table='tasks_tags')


class TimestampsTable(Table):

    def __init__(self, columns, parent=None, **options):
        super().__init__(columns, parent=parent, **options)
        self.table.column('stamp', width=200, anchor='w')
        self.table.column('since', width=150, anchor='w')
        self.table.column('comment', width=450, anchor='w')
        self.table.column('real', width=250, anchor='w')

    def sort_table_contents(self, col, reverse):
        """Sorting by click on column header."""
        if col == "stamp":
            shortlist = self._sort(0, reverse)
        elif col == "real":
            shortlist = self._sort(1, reverse)
        elif col == "since":
            shortlist = self._sort(2, reverse)
        else:
            return
        shortlist.sort(key=lambda x: x[0], reverse=reverse)
        for index, value in enumerate(shortlist):
            self.table.move(value[1], '', index)
        self.table.heading(
            col, command=lambda: self.sort_table_contents(col, not reverse))

    def update_timestamps_list(self, data):
        """Refill table contents."""
        self.update_data(data)
        for t in data:
            t[0] = core.time_format(int(t[0]))
            t[1] = core.table_date_format(t[1])
            t[2] = core.time_format(int(t[2]))
        self.insert_rows(data)


class TimestampsWindow(Window):
    """Window with timestamps for selected task."""

    def __init__(self, taskid, task_time, parent=None, **options):
        super().__init__(master=parent, **options)
        self.task_id = taskid
        self.task_time = task_time
        self.title("Timestamps: {}".format(
            self.db.find_by_clause('tasks', 'id', self.task_id, 'name')[0][0]))
        column_names = OrderedDict({"stamp": "Timestamp",
                                    "real": "Date and time",
                                    "since": "Time spent since",
                                    "comment": "Comment"})
        self.stamps_frame = TimestampsTable(column_names, parent=self)
        self.stamps_frame.grid(row=0, column=0, columnspan=2, sticky='news')
        elements.TaskButton(self, text="Select all",
                            command=self.stamps_frame.select_all).grid(
                                                          row=1, column=0,
                                                          pady=5, padx=5,
                                                          sticky='w')
        elements.TaskButton(self, text="Clear selection", textwidth=12,
                            command=self.stamps_frame.clear_all).grid(
                                                         row=1, column=1,
                                                         pady=5, padx=5,
                                                         sticky='e')
        tk.Frame(self, height=40).grid(row=2)
        self.update_table()
        elements.TaskButton(
            self, text="Delete...", command=self.delete).grid(
            row=3, column=0, pady=5, padx=5, sticky='w')
        elements.TaskButton(self, text="Close", command=self.destroy).grid(
            row=3, column=1, pady=5, padx=5, sticky='e')
        self.grid_columnconfigure(1, weight=1, minsize=500)
        self.grid_rowconfigure(0, weight=1, minsize=300)
        self.minsize(width=710, height=500)
        self.prepare()

    def update_table(self):
        db_contents = self.db.find_by_clause("timestamps", "task_id",
                                             self.task_id, "*")
        tlist = [{"stamp": timestamp[0], "datetime": timestamp[3],
                  "comment": timestamp[4],
                  "spent_since": self.task_time - timestamp[0]}
                 for timestamp in db_contents]
        self.stamps_frame.update_timestamps_list([[f["stamp"], f["datetime"],
                                                   f["spent_since"],
                                                   f["comment"]] for f in tlist])
        self.sdict = {}
        for n, task_id in enumerate(self.stamps_frame.table.get_children()):
            self.sdict[task_id] = tlist[n]

    def delete(self):
        """Deletes selected timestamps."""
        ids = self.stamps_frame.table.selection()
        dates = [self.sdict[x]["datetime"] for x in ids]
        if ids:
            answer = askyesno("Warning",
                              "Are you sure you want to delete "
                              "selected timestamps?",
                              parent=self)
            if answer:
                for x in dates:
                    self.db.delete(table="timestamps", datetime=x,
                                   task_id=self.task_id)

                self.stamps_frame.table.delete(*ids)
                for item in ids:
                    self.sdict.pop(item)


class HelpWindow(Window):
    """Help window."""

    def __init__(self, parent=None, text='', **options):
        super().__init__(master=parent, **options)
        self.title("Help")
        main_frame = tk.Frame(self)
        self.help_area = Description(main_frame, fontsize=elements.FONTSIZE + 2)
        self.help_area.insert(text)
        self.help_area.config(state='disabled')
        self.help_area.grid(row=0, column=0, sticky='news')
        main_frame.grid(row=0, column=0, sticky='news', padx=5, pady=5)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        elements.TaskButton(self, text='OK', command=self.destroy).grid(
            row=1, column=0, sticky='e', pady=5, padx=5)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.bind("<Escape>", lambda e: self.destroy())
        self.prepare()


class Tagslist(elements.ScrolledCanvas):
    """Tags list. Accepts tagslist: [[tag_id, [state, 'tagname']]],
    can be 0 or 1."""

    def __init__(self, tagslist, parent=None, orientation="vertical",
                 **options):
        super().__init__(parent=parent, orientation=orientation, **options)
        self.states_list = tagslist
        for item in self.states_list:
            # Saving tag state:
            state = item[1][0]
            # Inserting dynamic variable instead of the state:
            item[1][0] = tk.IntVar()
            # Connecting new checkbox with this dynamic variable:
            cb = elements.SimpleCheckbutton(self.content_frame, text=(
                item[1][1] + ' ' * 3 if orientation == "horizontal"
                else item[1][1]), variable=item[1][0])
            cb.pack(side=('left' if orientation == "horizontal" else 'bottom'),
                    anchor='w')
            # Setting dynamic variable value to previously saved state:
            item[1][0].set(state)


class FilterWindow(Window):
    """Filters window."""

    def __init__(self, parent=None, variable=None, **options):
        super().__init__(master=parent, **options)
        self.title("Filter")
        # IntVar instance: used to set 1 if some changes were made.
        # For optimization.
        self.changed_var = variable
        # Operating mode of the filter: "AND", "OR".
        self.operating_mode_var = tk.StringVar()
        # Lists of stored filter parameters:
        stored_dates = \
        self.db.find_by_clause('options', 'name', 'filter_dates', 'value')[0][
            0].split(',')
        stored_tags = \
        self.db.find_by_clause('options', 'name', 'filter_tags', 'value')[0][
            0].split(',')
        if stored_tags[0]:  # stored_tags[0] is string.
            stored_tags = list(map(int, stored_tags))
        # Dates list:
        dates = self.db.simple_dateslist()
        # Tags list:
        tags = self.db.simple_tagslist()
        # Checking checkboxes according to their values loaded from database:
        for tag in tags:
            if tag[0] in stored_tags:
                tag[1][0] = 1
        elements.SimpleLabel(self, text="Dates").grid(row=0, column=0,
                                                      sticky='n')
        elements.SimpleLabel(self, text="Tags").grid(row=0, column=1,
                                                     sticky='n')
        self.dates_list = Tagslist(
            [[x, [1 if x in stored_dates else 0, x]] for x in dates], self,
            width=200, height=300)
        self.tags_list = Tagslist(tags, self, width=200, height=300)
        self.dates_list.grid(row=1, column=0, pady=5, padx=5, sticky='news')
        self.tags_list.grid(row=1, column=1, pady=5, padx=5, sticky='news')
        elements.TaskButton(self, text="Select dates...", textwidth=15,
                            command=self.select_dates).grid(row=2, column=0,
                                                            pady=7, padx=5,
                                                            sticky='n')
        elements.TaskButton(self, text="Clear", command=self.clear_tags).grid(
            row=2, column=1, pady=7, padx=5, sticky='n')
        elements.TaskButton(self, text="Clear", command=self.clear_dates).grid(
            row=3, column=0, pady=7, padx=5, sticky='n')
        tk.Frame(self, height=20).grid(row=5, column=0, columnspan=2,
                                       sticky='news')
        elements.SimpleLabel(self, text="Filter operating mode:").grid(
            row=5, columnspan=2, pady=5)
        check_frame = tk.Frame(self)
        check_frame.grid(row=7, columnspan=2, pady=5)
        elements.SimpleRadiobutton(check_frame, text="AND",
                                   variable=self.operating_mode_var,
                                   value="AND").grid(row=0, column=0,
                                                     sticky='e')
        elements.SimpleRadiobutton(check_frame, text="OR",
                                   variable=self.operating_mode_var,
                                   value="OR").grid(row=0, column=1,
                                                    sticky='w')
        self.operating_mode_var.set(
            self.db.find_by_clause(table="options", field="name",
                                   value="filter_operating_mode",
                                   searchfield="value")[0][0])
        tk.Frame(self, height=20).grid(row=8, column=0, columnspan=2,
                                       sticky='news')
        elements.TaskButton(self, text="Cancel", command=self.destroy).grid(
            row=9, column=1, pady=5, padx=5, sticky='e')
        elements.TaskButton(self, text='Ok', command=self.apply_filter).grid(
            row=9, column=0, pady=5, padx=5, sticky='w')
        self.bind("<Return>", lambda e: self.apply_filter())
        self.minsize(height=350, width=350)
        self.maxsize(width=750, height=600)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(1, weight=1)
        self.prepare()

    def clear_dates(self):
        for x in self.dates_list.states_list:
            x[1][0].set(0)

    def clear_tags(self):
        for x in self.tags_list.states_list:
            x[1][0].set(0)

    def select_dates(self):
        """Pops up window where user can select dates interval."""
        start_date = tk.StringVar(self)
        end_date = tk.StringVar(self)
        correct = tk.DoubleVar(self)
        CalendarWindow(self, correct, startvar=start_date, endvar=end_date,
                       startdate=self.dates_list.states_list[-1][0],
                       enddate=self.dates_list.states_list[0][0])
        if correct.get():
            for date in self.dates_list.states_list:
                date[1][0].set(0)
                if core.str_to_date(start_date.get()) <= core.str_to_date(
                        date[0]) <= core.str_to_date(end_date.get()):
                    date[1][0].set(1)

    def apply_filter(self):
        """Create database script based on checkboxes values."""
        dates = list(reversed(
            [x[0] for x in self.dates_list.states_list if x[1][0].get() == 1]))
        tags = list(reversed(
            [x[0] for x in self.tags_list.states_list if x[1][0].get() == 1]))
        if not dates and not tags:
            script = None
            self.operating_mode_var.set("AND")
        else:
            script = core.prepare_filter_query(dates, tags,
                                               self.operating_mode_var.get())
        GLOBAL_OPTIONS["filter_dict"] = {
            'operating_mode': self.operating_mode_var.get(),
            'script': script,
            'tags': tags,
            'dates': dates
        }
        # Reporting to parent window that filter values have been changed:
        if self.changed_var:
            self.changed_var.set(1)
        self.destroy()


class CalendarWindow(Window):
    def __init__(self, parent=None, correct_data=None, startvar=None,
                 endvar=None, startdate=None, enddate=None, **options):
        super().__init__(master=parent, **options)
        self.title("Select dates")
        self.correct_data = correct_data
        self.start_var = startvar
        self.end_var = endvar
        self.start_date_entry = sel_cal.Datepicker(
            self, datevar=self.start_var,
            current_month=core.str_to_date(startdate).month,
            current_year=core.str_to_date(startdate).year)
        self.end_date_entry = sel_cal.Datepicker(
            self, datevar=self.end_var,
            current_month=core.str_to_date(enddate).month,
            current_year=core.str_to_date(enddate).year)
        elements.SimpleLabel(self, text="Enter first date:").grid(row=0,
                                                                  column=0,
                                                                  pady=3,
                                                                  padx=5,
                                                                  sticky='w')
        self.start_date_entry.grid(row=1, column=0, padx=5, pady=3, sticky='w')
        elements.SimpleLabel(self, text="Enter last date:").grid(row=2,
                                                                 column=0,
                                                                 pady=5,
                                                                 padx=5,
                                                                 sticky='w')
        self.end_date_entry.grid(row=3, column=0, padx=5, pady=3, sticky='w')
        tk.Frame(self, height=15, width=10).grid(row=4, column=0, columnspan=2)
        elements.TaskButton(self, text='OK', command=self.close).grid(
            row=5, column=0, padx=5, pady=5, sticky='w')
        elements.TaskButton(self, text='Cancel', command=self.destroy).grid(
            row=5, column=1, padx=5, pady=5, sticky='e')
        self.bind("<Return>", lambda e: self.close())
        self.minsize(height=350, width=450)
        self.maxsize(width=600, height=500)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.prepare()

    def close(self):
        try:
            core.str_to_date(self.start_var.get())
            core.str_to_date(self.end_var.get())
        except ValueError:
            self.correct_data.set(False)
        else:
            self.correct_data.set(True)
        finally:
            super().destroy()

    def destroy(self):
        self.correct_data.set(False)
        super().destroy()


class RightclickMenu(tk.Menu):
    """Popup menu. By default has one menuitem - "copy"."""

    def __init__(self, parent=None, copy_item=True, paste_item=False,
                 **options):
        super().__init__(master=parent, tearoff=0, **options)
        if copy_item:
            self.add_command(label="Copy", command=copy_to_clipboard)
        if paste_item:
            self.add_command(label="Paste", command=paste_from_clipboard)

    def context_menu_show(self, event):
        """Function links context menu with current selected widget
        and pops menu up."""
        self.tk_popup(event.x_root, event.y_root)
        GLOBAL_OPTIONS["selected_widget"] = event.widget


class MainFrame(elements.ScrolledCanvas):
    """Container for all task frames."""

    def __init__(self, parent):
        super().__init__(parent=parent, bd=2)
        self.frames_count = 0
        self.rows_counter = 0
        self.frames = []
        self.fill()

    def clear(self):
        """Remove all task frames except with opened tasks."""
        for w in self.content_frame.winfo_children():
            if self.frames_count == GLOBAL_OPTIONS['timers_count'] \
                    or self.frames_count == len(GLOBAL_OPTIONS["tasks"]):
                break
            if hasattr(w, 'task'):
                if w.task is None:
                    self.frames_count -= 1
                    w.destroy()

    def clear_all(self):
        """Clear all task frames."""
        answer = askyesno("Really clear?",
                          "Are you sure you want to close all task frames?")
        if answer:
            for w in self.content_frame.winfo_children():
                if hasattr(w, 'task'):
                    w.clear()
            self.fill()

    def frames_timer_indicator_update(self):
        """Explicitly reload timer in every task frame."""
        for frame in self.frames:
            if not frame.running:
                frame.configure_indicator()

    def fill(self):
        """Create contents of the main frame."""
        if self.frames_count < GLOBAL_OPTIONS['timers_count']:
            row_count = range(
                GLOBAL_OPTIONS['timers_count'] - self.frames_count)
            for _ in row_count:
                task = TaskFrame(parent=self.content_frame)
                task.grid(row=self.rows_counter, pady=5, padx=5, ipady=3,
                          sticky='ew')
                if GLOBAL_OPTIONS["preserved_tasks_list"]:
                    task_id = GLOBAL_OPTIONS["preserved_tasks_list"].pop(0)
                    task.get_restored_task_name(task_id)
                self.frames.append(task)
                self.rows_counter += 1
            self.frames_count += len(row_count)
            self.content_frame.update()
            self.canvbox.config(width=self.content_frame.winfo_width())
        elif len(GLOBAL_OPTIONS["tasks"]) < self.frames_count > \
                GLOBAL_OPTIONS['timers_count']:
            self.clear()
        self.content_frame.config(bg='#cfcfcf')

    def change_interface(self, interface):
        """Change interface type. Accepts keywords 'normal' and 'small'."""
        for widget in self.content_frame.winfo_children():
            try:
                if interface == 'normal':
                    widget.normal_interface()
                elif interface == 'small':
                    widget.small_interface()
            except TclError:
                pass

    def pause_all(self):
        for frame in self.frames:
            if frame.running:
                frame.timer_stop(paused=True)

    def resume_all(self):
        for frame in self.frames:
            if frame.paused:
                frame.timer_start(stop_all=False)

    def stop_all(self):
        for frame in self.frames:
            frame.timer_stop()


class MainMenu(tk.Menu):
    """Main window menu."""

    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        file = tk.Menu(self, tearoff=0)
        file.add_command(label="Options...", command=self.options_window,
                         underline=0)
        file.add_separator()
        file.add_command(label="Exit", command=self.exit, underline=1)
        elements.big_font(file, elements.FONTSIZE + 1)
        self.add_cascade(label="Main menu", menu=file, underline=0)
        helpmenu = tk.Menu(self, tearoff=0)
        helpmenu.add_command(label="Help...",
                             command=lambda: helpwindow(parent=ROOT_WINDOW,
                                                        text=core.HELP_TEXT))
        helpmenu.add_command(label="About...", command=self.aboutwindow)
        elements.big_font(helpmenu, elements.FONTSIZE + 1)
        self.add_cascade(label="Help", menu=helpmenu)
        elements.big_font(self, elements.FONTSIZE + 1)

    def options_window(self):
        """Open options window."""
        self.db = core.Db()
        # number of main window frames:
        timers_count_var = tk.IntVar(value=GLOBAL_OPTIONS['timers_count'])
        # 'always on top' option:
        ontop = tk.IntVar(value=GLOBAL_OPTIONS['always_on_top'])
        # 'compact interface' option
        compact = GLOBAL_OPTIONS['compact_interface']
        compact_iface = tk.IntVar(value=compact)
        # 'save tasks on exit' option:
        save = tk.IntVar(value=GLOBAL_OPTIONS['preserve_tasks'])
        # 'show current day in timers' option:
        show_today_var = tk.IntVar(value=GLOBAL_OPTIONS['show_today'])
        toggle = GLOBAL_OPTIONS['toggle_tasks']
        toggler_var = tk.IntVar(value=toggle)
        params = {}
        accept_var = tk.BooleanVar()
        Options(ROOT_WINDOW, accept_var, timers_count_var, ontop,
                compact_iface, save, show_today_var, toggler_var)
        if accept_var.get():
            try:
                count = timers_count_var.get()
            except tk.TclError:
                pass
            else:
                if count < 1:
                    count = 1
                elif count > GLOBAL_OPTIONS["MAX_TASKS"]:
                    count = GLOBAL_OPTIONS["MAX_TASKS"]
                params['timers_count'] = count
            # apply value of 'always on top' option:
            params['always_on_top'] = ontop.get()
            ROOT_WINDOW.wm_attributes("-topmost", params['always_on_top'])
            # apply value of 'compact interface' option:
            params['compact_interface'] = compact_iface.get()
            if compact != compact_iface.get():
                if compact_iface.get() == 0:
                    ROOT_WINDOW.full_interface()
                elif compact_iface.get() == 1:
                    ROOT_WINDOW.small_interface()
            # apply value of 'save tasks on exit' option:
            params['preserve_tasks'] = save.get()
            if not params['preserve_tasks']:
                self.db.update_preserved_tasks('')
            # apply value of 'show current day in timers' option:
            params['show_today'] = show_today_var.get()
            # apply value of 'Allow run only one task at a time' option:
            params['toggle_tasks'] = toggler_var.get()
            # save all parameters to DB:
            self.change_parameter(params)
            # redraw taskframes if needed:
            ROOT_WINDOW.taskframes.fill()
            ROOT_WINDOW.taskframes.frames_timer_indicator_update()
            # Stop all tasks if exclusive run method has been enabled:
            if params['toggle_tasks'] and params['toggle_tasks'] != toggle:
                if len([x for x in GLOBAL_OPTIONS["tasks"].values() if x]) != 1:
                    ROOT_WINDOW.stop_all()
                paused = get_paused_taskframes()
                if len(paused) > 1:
                    ROOT_WINDOW.change_paused_state()
                    for x in paused:
                        x.paused = False
        ROOT_WINDOW.lift()

    def change_parameter(self, paramdict):
        """Change option in the database."""
        for key, value in paramdict.items():
            self.db.update(table='options', field='value', value=value,
                           field_id=key, updfield='name')
            GLOBAL_OPTIONS[key] = value
        self.db.con.close()

    def aboutwindow(self):
        showinfo("About %s" % core.TITLE,
                 core.ABOUT_MESSAGE.format(
                     GLOBAL_OPTIONS['version'],
                     core.CREATOR_NAME,
                     datetime.datetime.strftime(datetime.datetime.now(), "%Y")))

    def exit(self):
        ROOT_WINDOW.destroy()


class Options(Window):
    """Options window which can be opened from main menu."""

    def __init__(self, parent, is_applied, counter, on_top, compact, preserve,
                 show_today, toggler, **options):
        super().__init__(master=parent, width=300, height=200, **options)
        self.is_applied = is_applied
        self.title("Options")
        self.resizable(height=0, width=0)
        self.counter = counter
        elements.SimpleLabel(self, text="Task frames in main window: ").grid(
            row=0, column=0, sticky='w')
        counter_frame = tk.Frame(self)
        fontsize = elements.FONTSIZE
        elements.CanvasButton(counter_frame, text='<', command=self.decrease,
                              fontsize=fontsize, height=fontsize * 3).grid(
            row=0, column=0)
        elements.SimpleEntry(counter_frame, width=3, textvariable=counter,
                             justify='center').grid(row=0, column=1,
                                                    sticky='e')
        elements.CanvasButton(counter_frame, text='>', command=self.increase,
                              fontsize=fontsize, height=fontsize * 3).grid(
            row=0, column=2)
        counter_frame.grid(row=0, column=1)
        tk.Frame(self, height=20).grid(row=1)
        elements.SimpleLabel(self, text="Always on top: ").grid(row=2,
                                                                column=0,
                                                                sticky='w',
                                                                padx=5)
        elements.SimpleCheckbutton(self, variable=on_top).grid(row=2, column=1,
                                                               sticky='w',
                                                               padx=5)
        elements.SimpleLabel(self, text="Compact interface: ").grid(row=3,
                                                                    column=0,
                                                                    sticky='w',
                                                                    padx=5)
        elements.SimpleCheckbutton(self, variable=compact).grid(row=3,
                                                                column=1,
                                                                sticky='w',
                                                                padx=5)
        elements.SimpleLabel(self, text="Save tasks on exit: ").grid(
            row=4, column=0, sticky='w', padx=5)
        elements.SimpleCheckbutton(self, variable=preserve).grid(row=4,
                                                                 column=1,
                                                                 sticky='w',
                                                                 padx=5)
        elements.SimpleLabel(self,
                             text="Show time for current day only "
                                  "in timer's window: ").grid(
            row=5, column=0, sticky='w', padx=5)
        elements.SimpleCheckbutton(self, variable=show_today).grid(row=5,
                                                                   column=1,
                                                                   sticky='w',
                                                                   padx=5)
        elements.SimpleLabel(self,
                             text="Allow to run only "
                                  "one task at a time: ").grid(
            row=6, column=0, sticky='w', padx=5)
        elements.SimpleCheckbutton(self, variable=toggler).grid(row=6,
                                                                column=1,
                                                                sticky='w',
                                                                padx=5)
        tk.Frame(self, height=20).grid(row=7)
        elements.TaskButton(self, text='OK', command=self.apply).grid(
            row=8, column=0, sticky='w', padx=5, pady=5)
        elements.TaskButton(self, text='Cancel', command=self.destroy).grid(
            row=8, column=1, sticky='e', padx=5, pady=5)
        self.bind("<Return>", lambda e: self.apply())
        self.prepare()

    def apply(self):
        self.is_applied.set(True)
        self.destroy()

    def increase(self):
        if self.counter.get() < GLOBAL_OPTIONS["MAX_TASKS"]:
            self.counter.set(self.counter.get() + 1)

    def decrease(self):
        if self.counter.get() > 1:
            self.counter.set(self.counter.get() - 1)


class ExportWindow(Window):
    """Export dialogue window."""

    def __init__(self, parent, data, **options):
        super().__init__(master=parent, **options)
        self.title("Export parameters")
        self.task_ids = [x["id"] for x in data.values()]
        self.operating_mode_var = tk.IntVar(self)
        elements.SimpleLabel(self, text="Export mode", fontsize=elements.FONTSIZE + 1).grid(
            row=0, column=0, columnspan=2, sticky='ns', pady=5)
        elements.SimpleRadiobutton(self, text="Task-based",
                                   variable=self.operating_mode_var,
                                   value=0).grid(row=1, column=0)
        elements.SimpleRadiobutton(self, text="Date-based",
                                   variable=self.operating_mode_var,
                                   value=1).grid(row=1, column=1)
        tk.Frame(self, height=15).grid(row=2, column=0)
        elements.TaskButton(self, text="Export", command=self.get_data).grid(
            row=3, column=0, padx=5, pady=5, sticky='ws')
        elements.TaskButton(self, text="Cancel", command=self.destroy).grid(
            row=3, column=1, padx=5, pady=5, sticky='es')
        self.minsize(height=150, width=250)
        self.maxsize(width=450, height=300)
        self.grid_columnconfigure('all', weight=1)
        self.grid_rowconfigure('all', weight=1)
        self.prepare()

    def get_data(self):
        """Take from the database information to be exported and prepare it.
        All items should be strings."""
        if self.operating_mode_var.get() == 0:
            prepared_data = self.db.tasks_to_export(self.task_ids)
        else:
            prepared_data = self.db.dates_to_export(self.task_ids)
        self.export('\n'.join(prepared_data))

    def export(self, data):
        while True:
            filename = asksaveasfilename(parent=self, defaultextension=".csv",
                                         filetypes=[("All files", "*.*"), (
                                         "Comma-separated texts", "*.csv")])
            if filename:
                try:
                    core.write_to_disk(filename, data)
                except PermissionError:
                    showinfo("Unable to save file",
                             "No permission to save file here!"
                             "Please select another location.")
                else:
                    break
            else:
                break
        self.destroy()


class MainWindow(tk.Tk):
    def __init__(self, **options):
        super().__init__(**options)
        # Default widget colour:
        GLOBAL_OPTIONS["colour"] = self.cget('bg')
        self.title(core.TITLE)
        self.minsize(height=75, width=0)
        self.resizable(width=0, height=1)
        main_menu = MainMenu(self)  # Create main menu.
        self.config(menu=main_menu)
        self.taskframes = MainFrame(self)  # Main window content.
        self.taskframes.grid(row=0, columnspan=5)
        self.bind("<Configure>", self.taskframes.reconf_canvas)
        self.paused = False
        if not GLOBAL_OPTIONS["compact_interface"]:
            self.full_interface(True)
        self.grid_rowconfigure(0, weight=1)
        # Make main window always appear in good position
        # and with adequate size:
        self.update()
        if self.winfo_height() < self.winfo_screenheight() - 250:
            window_height = self.winfo_height()
        else:
            window_height = self.winfo_screenheight() - 250
        self.geometry('%dx%d+100+50' % (self.winfo_width(), window_height))
        if GLOBAL_OPTIONS['always_on_top']:
            self.wm_attributes("-topmost", 1)
        self.bind("<Key>", self.hotkeys)

    def hotkeys(self, event):
        """Execute corresponding actions for hotkeys."""
        if event.keysym in ('Cyrillic_yeru', 'Cyrillic_YERU', 's', 'S'):
            self.stop_all()
        elif event.keysym in ('Cyrillic_es', 'Cyrillic_ES', 'c', 'C'):
            self.taskframes.clear_all()
        elif event.keysym in (
        'Cyrillic_shorti', 'Cyrillic_SHORTI', 'q', 'Q', 'Escape'):
            self.destroy()
        elif event.keysym in ('Cyrillic_ZE', 'Cyrillic_ze', 'p', 'P'):
            self.pause_all()

    def full_interface(self, firstrun=False):
        """Create elements which are displayed in full interface mode."""
        self.add_frame = tk.Frame(self, height=35)
        self.add_frame.grid(row=1, columnspan=5)
        self.stop_button = elements.TaskButton(self, text="Stop all",
                                               command=self.stop_all)
        self.stop_button.grid(row=2, column=2, sticky='sn', pady=5, padx=5)
        self.clear_button = elements.TaskButton(
            self, text="Clear all",
            command=self.taskframes.clear_all)
        self.clear_button.grid(row=2, column=0, sticky='wsn', pady=5,
                               padx=5)
        self.pause_all_var = tk.StringVar(value="Resume all" if self.paused
                                          else "Pause all")
        self.pause_button = elements.TaskButton(self,
                                                variable=self.pause_all_var,
                                                command=self.pause_all,
                                                textwidth=10)
        self.pause_button.grid(row=2, column=3, sticky='snw', pady=5,
                               padx=5)
        self.add_quit_button = elements.TaskButton(self, text="Quit",
                                                   command=self.destroy)
        self.add_quit_button.grid(row=2, column=4, sticky='sne', pady=5,
                                  padx=5)
        if not firstrun:
            self.taskframes.change_interface('normal')

    def small_interface(self):
        """Destroy all additional interface elements."""
        for widget in (self.add_frame, self.stop_button,
                       self.clear_button, self.add_quit_button,
                       self.pause_button):
            widget.destroy()
        self.taskframes.change_interface('small')

    def change_paused_state(self, paused=False):
        self.paused = paused
        if not GLOBAL_OPTIONS["compact_interface"]:
            if paused:
                title = "Resume all"
            else:
                title = "Pause all"
            self.pause_all_var.set(title)

    def pause_all(self):
        if self.paused:
            self.taskframes.resume_all()
            self.change_paused_state()
        else:
            self.taskframes.pause_all()
            self.change_paused_state(True)

    def stop_all(self):
        """Stop all running timers."""
        self.taskframes.stop_all()
        self.paused = False
        self.change_paused_state()

    def destroy(self):
        answer = askyesno("Quit confirmation", "Do you really want to quit?")
        if answer:
            db = core.Db()
            if GLOBAL_OPTIONS["preserve_tasks"]:
                tasks = GLOBAL_OPTIONS["tasks"]
                if int(GLOBAL_OPTIONS['timers_count']) < len(
                        GLOBAL_OPTIONS["tasks"]):
                    db.update(table='options', field='value',
                              value=len(GLOBAL_OPTIONS["tasks"]),
                              field_id='timers_count', updfield='name')
            else:
                tasks = ''
            db.update_preserved_tasks(tasks)
            db.con.close()
            super().destroy()


def get_paused_taskframes():
    res = []
    for widget in ROOT_WINDOW.taskframes.content_frame.winfo_children():
        if hasattr(widget, "paused"):
            if widget.paused:
                res.append(widget)
    return res


def helpwindow(parent=None, text=None):
    """Show simple help window with given text."""
    HelpWindow(parent, text)


def copy_to_clipboard():
    """Copy widget text to clipboard."""
    GLOBAL_OPTIONS["selected_widget"].clipboard_clear()
    if isinstance(GLOBAL_OPTIONS["selected_widget"], tk.Text):
        try:
            GLOBAL_OPTIONS["selected_widget"].clipboard_append(
                GLOBAL_OPTIONS["selected_widget"].selection_get())
        except tk.TclError:
            GLOBAL_OPTIONS["selected_widget"].clipboard_append(
                GLOBAL_OPTIONS["selected_widget"].get(1.0, 'end'))
    else:
        GLOBAL_OPTIONS["selected_widget"].clipboard_append(
            GLOBAL_OPTIONS["selected_widget"].cget("text"))


def paste_from_clipboard():
    """Paste text from clipboard."""
    if isinstance(GLOBAL_OPTIONS["selected_widget"], tk.Text):
        GLOBAL_OPTIONS["selected_widget"].insert(tk.INSERT, GLOBAL_OPTIONS[
            "selected_widget"].clipboard_get())
    elif isinstance(GLOBAL_OPTIONS["selected_widget"], tk.Entry):
        GLOBAL_OPTIONS["selected_widget"].insert(0, GLOBAL_OPTIONS[
            "selected_widget"].clipboard_get())


def get_options():
    """Get program preferences from database."""
    db = core.Db()
    return {x[0]: x[1] for x in db.find_all(table='options')}


if __name__ == "__main__":
    # Maximum number of task frames:
    MAX_TASKS = 10
    # Interval between timer renewal:
    TIMER_INTERVAL = 250
    # Interval between saving time to database:
    SAVE_INTERVAL = 10000  # ms
    # Check if tasks database actually exists:
    core.check_database()
    # Create options dictionary:
    GLOBAL_OPTIONS = get_options()
    # Global tasks ids set. Used for preserve duplicates:
    if GLOBAL_OPTIONS["tasks"]:
        GLOBAL_OPTIONS["tasks"] = dict.fromkeys(
            map(int, str(GLOBAL_OPTIONS["tasks"]).split(",")), False)
    else:
        GLOBAL_OPTIONS["tasks"] = dict()
    # List of preserved tasks which are not open:
    GLOBAL_OPTIONS["preserved_tasks_list"] = list(GLOBAL_OPTIONS["tasks"])
    # Widget which is currently connected to context menu:
    GLOBAL_OPTIONS["selected_widget"] = None
    GLOBAL_OPTIONS.update({"MAX_TASKS": MAX_TASKS,
                           "TIMER_INTERVAL": TIMER_INTERVAL,
                           "SAVE_INTERVAL": SAVE_INTERVAL})
    # Main window:
    ROOT_WINDOW = MainWindow()
    ROOT_WINDOW.mainloop()