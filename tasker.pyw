#!/usr/bin/env python3

import copy
import datetime
import time

try:
    import tkinter as tk
except ModuleNotFoundError:
    import sys

    sys.exit(
        "Unable to start GUI. Please install Tk for Python: "
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
        ontop = GLOBAL_OPTIONS['always_on_top']
        if ontop == '1':
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
        self.startstopvar = tk.StringVar()  # Text on "Start" button.
        self.startstopvar.set("Start")
        # Fake name of running task (which actually is not selected yet).
        self.task = None
        self.task_id = None
        self.description = None
        if GLOBAL_OPTIONS["compact_interface"] == "0":
            self.normal_interface()
        # Task name field:
        self.tasklabel = TaskLabel(self, width=50, anchor='w')
        elements.big_font(self.tasklabel, size=14)
        self.tasklabel.grid(row=1, column=0, columnspan=5, padx=5, pady=5,
                            sticky='w')
        self.openbutton = elements.TaskButton(self, text="Task...",
                                              command=self.name_dialogue)
        self.openbutton.grid(row=1, column=5, padx=5, pady=5, sticky='e')
        self.startbutton = elements.CanvasButton(
            self, state='disabled',
            fontsize=14,
            command=self.startstopbutton,
            variable=self.startstopvar,
            image='resource/start_disabled.png' if tk.TkVersion >= 8.6
            else 'resource/start_disabled.pgm',
            opacity='left')
        self.startbutton.grid(row=3, column=0, sticky='wsn', padx=5)
        # Counter frame:
        self.timer_window = TaskLabel(self, width=10, state='disabled')
        elements.big_font(self.timer_window, size=20)
        self.timer_window.grid(row=3, column=1, pady=5)
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
        self.properties = elements.TaskButton(self, text="Properties...",
                                              textwidth=9, state='disabled',
                                              command=self.properties_window)
        self.properties.grid(row=3, column=4, sticky='e', padx=5)
        # Clear frame button:
        self.clearbutton = elements.TaskButton(self, text='Clear',
                                               state='disabled', textwidth=7,
                                               command=self.clear)
        self.clearbutton.grid(row=3, column=5, sticky='e', padx=5)
        self.running_time = 0  # Current value of the counter.
        self.running = False
        self.timestamp = 0

    def normal_interface(self):
        """Creates elements which are visible only in full interface mode."""
        # 'Task name' text:
        self.l1 = tk.Label(self, text='Task name:')
        elements.big_font(self.l1, size=12)
        self.l1.grid(row=0, column=1, columnspan=3)
        # Task description field:
        self.description = Description(self, width=60, height=3)
        self.description.grid(row=2, column=0, columnspan=6, padx=5, pady=6,
                              sticky='we')
        if self.task:
            self.description.update_text(self.task[3])

    def small_interface(self):
        """Destroy some interface elements when switching to 'compact' mode."""
        for widget in self.l1, self.description:
            widget.destroy()
        self.description = None

    def timestamps_window(self):
        """Timestamps window opening."""
        TimestampsWindow(self.task_id, self.running_time, run)

    def add_timestamp(self):
        """Adding timestamp to database."""
        self.db.insert('timestamps', ('task_id', 'timestamp'),
                       (self.task_id, self.running_time))
        showinfo("Timestamp added", "Timestamp added.")

    def startstopbutton(self):
        """Changes "Start/Stop" button state. """
        if self.running:
            self.timer_stop()
        else:
            self.timer_start()

    def properties_window(self):
        """Task properties window."""
        edited = tk.IntVar()
        TaskEditWindow(self.task[0], parent=run, variable=edited)
        if edited.get() == 1:
            self.update_description()

    def clear(self):
        """Recreation of frame contents."""
        self.timer_stop()
        for w in self.winfo_children():
            w.destroy()
        GLOBAL_OPTIONS["tasks"].pop(self.task[0])
        self.create_content()

    def name_dialogue(self):
        """Task selection window."""
        var = tk.IntVar()
        TaskSelectionWindow(run, taskvar=var)
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
                GLOBAL_OPTIONS["tasks"].pop(self.task[0])
            self.get_restored_task_name(task_id)
        else:
            # If selected task is already opened in another frame:
            if self.task_id != task_id:
                showinfo("Task exists", "Task is already opened.")

    def get_restored_task_name(self, taskid):
        self.task_id = taskid
        # Preparing new task:
        self.prepare_task(
            self.db.select_task(self.task_id))  # Task parameters from database

    def prepare_task(self, task):
        """Prepares frame elements to work with."""
        # Adding task id to set of running tasks:
        GLOBAL_OPTIONS["tasks"][task[0]] = False
        self.task = task
        self.current_date = core.date_format(datetime.datetime.now())
        # Set current time, just for this day:
        if self.task[-1] is None:
            self.date_exists = False
            self.task[-1] = 0
        else:
            self.date_exists = True
        # Taking current counter value from database:
        self.set_current_time()
        self.timer_window.config(text=core.time_format(self.running_time))
        self.tasklabel.config(text=self.task[1])
        self.startbutton.config(state='normal')
        self.startbutton.config(image='resource/start_normal.png'
                                if tk.TkVersion >= 8.6
                                else 'resource/start_normal.pgm')
        self.properties.config(state='normal')
        self.clearbutton.config(state='normal')
        self.timer_window.config(state='normal')
        self.add_timestamp_button.config(state='normal')
        self.timestamps_window_button.config(state='normal')
        if self.description:
            self.description.update_text(self.task[3])

    def set_current_time(self):
        """Set current_time depending on time displaying options value."""
        if int(GLOBAL_OPTIONS["show_today"]):
            self.running_time = self.task[5]
        else:
            self.running_time = self.task[2]

    def reload_timer(self):
        """Used for task data reloading
        without explicitly redrawing anything but timer."""
        self.timer_stop()
        self.task = self.db.select_task(self.task_id)
        self.set_current_time()
        self.timer_start()

    def check_date(self):
        """Used to check if date has been changed
        since last timer value save."""
        current_date = core.date_format(datetime.datetime.now())
        if current_date != self.current_date:
            self.current_date = current_date
            self.date_exists = False
            self.running_today_time = self.running_today_time - self.timestamp
            self.start_today_time = time.time() - self.running_today_time
        self.task_update()

    def task_update(self):
        """Updates time in the database."""
        if not self.date_exists:
            self.db.insert("activity", ("date", "task_id", "spent_time"),
                           (self.current_date, self.task[0],
                            self.running_today_time))
            self.date_exists = True
        # self.reload_timer()
        else:
            self.db.update_task(self.task[0], value=self.running_today_time)
        self.timestamp = self.running_today_time

    def timer_update(self, counter=0):
        """Renewal of the counter."""
        # Time interval in milliseconds
        # before next iteration of recursion:
        interval = 250
        self.running_time = time.time() - self.start_time
        self.running_today_time = time.time() - self.start_today_time
        self.timer_window.config(text=core.time_format(
            self.running_time if self.running_time < 86400
            else self.running_today_time))
        if GLOBAL_OPTIONS["tasks"][self.task_id]:
            # Every n seconds counter value is saved in database:
            if counter >= GLOBAL_OPTIONS["SAVE_INTERVAL"]:
                self.check_date()
                counter = 0
            else:
                counter += interval
            # self.timer variable becomes ID created by after():
            self.timer = self.timer_window.after(interval, self.timer_update,
                                                 counter)
        else:
            self.timer_stop()

    def timer_start(self):
        """Counter start."""
        if not self.running:
            GLOBAL_OPTIONS["stopall"] = False
            if int(GLOBAL_OPTIONS["toggle_tasks"]):
                for key in GLOBAL_OPTIONS["tasks"]:
                    GLOBAL_OPTIONS["tasks"][key] = False
            GLOBAL_OPTIONS["tasks"][self.task_id] = True
            # Setting current counter value:
            self.start_time = time.time() - self.running_time
            # This value is used to add record to database:
            self.start_today_time = time.time() - self.task[-1]
            self.timer_update()
            self.running = True
            self.startbutton.config(
                image='resource/stop.png' if tk.TkVersion >= 8.6
                else 'resource/stop.pgm')
            self.startstopvar.set("Stop")

    def timer_stop(self):
        """Stop counter and save its value to database."""
        if self.running:
            # after_cancel() stops execution of callback with given ID.
            self.timer_window.after_cancel(self.timer)
            self.running_time = time.time() - self.start_time
            self.running_today_time = time.time() - self.start_today_time
            self.running = False
            GLOBAL_OPTIONS["tasks"][self.task_id] = False
            # Writing value into database:
            self.check_date()
            self.task[2] = self.running_time
            self.task[5] = self.running_today_time
            self.update_description()
            self.startbutton.config(
                image='resource/start_normal.png' if tk.TkVersion >= 8.6
                else 'resource/start_normal.pgm')
            self.startstopvar.set("Start")

    def update_description(self):
        """Update text in "Description" field."""
        self.task[3] = \
        self.db.find_by_clause("tasks", "id", self.task[0],
                               "description")[0][0]
        if self.description:
            self.description.update_text(self.task[3])

    def destroy(self):
        """Closes frame and writes counter value into database."""
        self.timer_stop()
        if self.task:
            GLOBAL_OPTIONS["tasks"].pop(self.task[0])
        self.db.con.close()
        tk.Frame.destroy(self)


class TaskList(tk.Frame):
    """Scrollable tasks table."""

    def __init__(self, columns, parent=None, **options):
        super().__init__(master=parent, **options)
        self.taskslist = ttk.Treeview(self)  # A table.
        style = ttk.Style()
        style.configure(".", font=('Helvetica', 11))
        style.configure("Treeview.Heading", font=('Helvetica', 11))
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.taskslist.yview)
        self.taskslist.config(yscrollcommand=scroller.set)
        scroller.pack(side='right', fill='y')
        self.taskslist.pack(fill='both', expand=1)
        # Creating and naming columns:
        self.taskslist.config(columns=tuple([col[0] for col in columns]))
        for index, col in enumerate(columns):
            # Configuring columns with given ids:
            self.taskslist.column(columns[index][0], width=100, minwidth=100,
                                  anchor='center')
            # Configuring headers of columns with given ids:
            self.taskslist.heading(columns[index][0], text=columns[index][1],
                                   command=lambda c=columns[index][0]:
                                   self.sortlist(c, True))
        self.taskslist.column('#0', anchor='w', width=70, minwidth=50,
                              stretch=0)
        self.taskslist.column('taskname', width=600, anchor='w')

    def sortlist(self, col, reverse):
        """Sorting by click on column header."""
        if col == "time":
            shortlist = self._sort(1, reverse)
        elif col == "date":
            shortlist = self._sort(2, reverse)
        else:
            shortlist = self._sort(0, reverse)
        shortlist.sort(key=lambda x: x[0], reverse=reverse)
        for index, value in enumerate(shortlist):
            self.taskslist.move(value[1], '', index)
        self.taskslist.heading(col,
                               command=lambda: self.sortlist(col, not reverse))

    def _sort(self, position, reverse):
        l = []
        for index, task in enumerate(self.taskslist.get_children()):
            l.append((self.tasks[index][position], task))
        # Sort tasks list by corresponding field to match current sorting:
        self.tasks.sort(key=lambda x: x[position], reverse=reverse)
        return l

    def insert_tasks(self, tasks):
        """Insert rows in the table. Row contents
        are tuples provided by 'values='."""
        for i, v in enumerate(tasks):  # item, number, value:
            self.taskslist.insert('', i, text="#%d" % (i + 1), values=v)

    def update_list(self, tasks):
        """Refill table contents."""
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.tasks = copy.deepcopy(tasks)
        for t in tasks:
            t[1] = core.time_format(t[1])
        self.insert_tasks(tasks)

    def focus_(self, item):
        """Focuses on the row with provided id."""
        self.taskslist.see(item)
        self.taskslist.selection_set(item)
        self.taskslist.focus_set()
        self.taskslist.focus(item)


class TaskSelectionWindow(Window):
    """Task selection and creation window."""

    def __init__(self, parent=None, taskvar=None, **options):
        super().__init__(master=parent, **options)
        # Variable which will contain selected task id:
        if taskvar:
            self.taskidvar = taskvar
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
        self.addentry = elements.SimpleEntry(self, width=50)
        self.addentry.grid(row=0, column=1, columnspan=3, sticky='we')
        # Enter adds new task:
        self.addentry.bind('<Return>', lambda event: self.add_new_task())
        self.addentry.focus_set()
        # Context menu with 'Paste' option:
        addentry_context_menu = RightclickMenu(paste_item=1, copy_item=0)
        self.addentry.bind("<Button-3>",
                           addentry_context_menu.context_menu_show)
        # "Add task" button:
        self.addbutton = elements.TaskButton(self, text="Add task",
                                             command=self.add_new_task,
                                             takefocus=False)
        self.addbutton.grid(row=0, column=4, sticky='e', padx=6, pady=5)
        # Entry for typing search requests:
        self.searchentry = elements.SimpleEntry(self, width=25)
        self.searchentry.grid(row=1, column=1, columnspan=2, sticky='we',
                              padx=5, pady=5)
        searchentry_context_menu = RightclickMenu(paste_item=1, copy_item=0)
        self.searchentry.bind("<Button-3>",
                              searchentry_context_menu.context_menu_show)
        # Case sensitive checkbutton:
        self.ignore_case = tk.IntVar(self, value=1)
        elements.SimpleCheckbutton(self, text="Ignore case", takefocus=False,
                                   variable=self.ignore_case).grid(row=1,
                                                                   column=0,
                                                                   padx=6,
                                                                   pady=5,
                                                                   sticky='w')
        # Search button:
        elements.CanvasButton(self, takefocus=False, text='Search',
                              image='resource/magnifier.png'
                              if tk.TkVersion >= 8.6
                              else 'resource/magnifier.pgm',
                              command=self.locate_task).grid(row=1, column=3,
                                                             sticky='w',
                                                             padx=5, pady=5)
        # Refresh button:
        elements.TaskButton(self, takefocus=False,
                            image='resource/refresh.png'
                            if tk.TkVersion >= 8.6 else 'resource/refresh.pgm',
                            command=self.update_list).grid(row=1, column=4,
                                                           sticky='e', padx=5,
                                                           pady=5)
        # Naming of columns in tasks list:
        columnnames = [('taskname', 'Task name'), ('time', 'Spent time'),
                       ('date', 'Creation date')]
        # Scrollable tasks table:
        self.listframe = TaskList(columnnames, self, takefocus=True)
        self.listframe.grid(row=2, column=0, columnspan=5, pady=10,
                            sticky='news')
        elements.SimpleLabel(self, text="Summary time:").grid(row=3, column=0,
                                                              pady=5, padx=5,
                                                              sticky='w')
        # Summarized time of all tasks in the table:
        self.fulltime_frame = TaskLabel(self, width=13, anchor='center')
        self.fulltime_frame.grid(row=3, column=1, padx=6, pady=5, sticky='e')
        # Selected task description:
        self.description = Description(self, height=4)
        self.description.grid(row=3, column=2, rowspan=2, pady=5, padx=5,
                              sticky='news')
        # "Select all" button:
        selbutton = elements.TaskButton(self, text="Select all",
                                        command=self.select_all)
        selbutton.grid(row=4, column=0, sticky='w', padx=5, pady=5)
        # "Clear all" button:
        clearbutton = elements.TaskButton(self, text="Clear all",
                                          command=self.clear_all)
        clearbutton.grid(row=4, column=1, sticky='e', padx=5, pady=5)
        # Task properties button:
        self.editbutton = elements.TaskButton(self, text="Properties...",
                                              textwidth=10, command=self.edit)
        self.editbutton.grid(row=3, column=3, sticky='w', padx=5, pady=5)
        # Remove task button:
        self.delbutton = elements.TaskButton(self, text="Remove...",
                                             textwidth=10, command=self.delete)
        self.delbutton.grid(row=4, column=3, sticky='w', padx=5, pady=5)
        # Export button:
        self.exportbutton = elements.TaskButton(self, text="Export...",
                                                command=self.export)
        self.exportbutton.grid(row=4, column=4, padx=5, pady=5, sticky='e')
        # Filter button:
        self.filterbutton = elements.TaskButton(self, text="Filter...",
                                                command=self.filterwindow)
        self.filterbutton.grid(row=3, column=4, padx=5, pady=5, sticky='e')
        # Filter button context menu:
        filter_context_menu = RightclickMenu(copy_item=False)
        filter_context_menu.add_command(label='Clear filter',
                                        command=self.apply_filter)
        self.filterbutton.bind("<Button-3>",
                               filter_context_menu.context_menu_show)
        tk.Frame(self, height=40).grid(row=5, columnspan=5, sticky='news')
        self.grid_columnconfigure(2, weight=1, minsize=50)
        self.grid_rowconfigure(2, weight=1, minsize=50)
        self.update_list()  # Fill table contents.
        self.current_task = ''  # Current selected task.
        self.listframe.taskslist.bind("<Down>", self.descr_down)
        self.listframe.taskslist.bind("<Up>", self.descr_up)
        self.listframe.taskslist.bind("<Button-1>", self.descr_click)
        self.listframe.bind("<FocusIn>",
                            lambda e: self.focus_first_item(forced=False))
        # Need to avoid masquerading of default ttk.Treeview action
        # on Shift+click and Control+click:
        self.modifier_pressed = False
        self.listframe.taskslist.bind("<KeyPress-Shift_L>",
                                      lambda e: self.shift_control_pressed())
        self.listframe.taskslist.bind("<KeyPress-Shift_R>",
                                      lambda e: self.shift_control_pressed())
        self.listframe.taskslist.bind("<KeyPress-Control_L>",
                                      lambda e: self.shift_control_pressed())
        self.listframe.taskslist.bind("<KeyPress-Control_R>",
                                      lambda e: self.shift_control_pressed())
        self.listframe.taskslist.bind("<KeyRelease-Shift_L>",
                                      lambda e: self.shift_control_released())
        self.listframe.taskslist.bind("<KeyRelease-Shift_R>",
                                      lambda e: self.shift_control_released())
        self.listframe.taskslist.bind("<KeyRelease-Control_L>",
                                      lambda e: self.shift_control_released())
        self.listframe.taskslist.bind("<KeyRelease-Control_R>",
                                      lambda e: self.shift_control_released())
        self.searchentry.bind("<Return>", lambda e: self.locate_task())
        self.bind("<F5>", lambda e: self.update_list())
        elements.TaskButton(self, text="Open", command=self.get_task).grid(
            row=6, column=0, padx=5, pady=5, sticky='w')
        elements.TaskButton(self, text="Cancel", command=self.destroy).grid(
            row=6, column=4, padx=5, pady=5, sticky='e')
        self.listframe.taskslist.bind("<Return>", self.get_task_id)
        self.listframe.taskslist.bind("<Double-1>", self.get_task_id)
        self.prepare()

    def check_row(self, event):
        """Check if mouse click is over the row,
        not another taskslist element."""
        if (event.type == '4' and len(
                self.listframe.taskslist.identify_row(event.y)) > 0) or (
                event.type == '2'):
            return True

    def get_task(self):
        """Get selected task id from database and close window."""
        # List of selected tasks item id's:
        tasks = self.listframe.taskslist.selection()
        if tasks:
            self.taskidvar.set(self.tdict[tasks[0]][0])
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
        if self.listframe.taskslist.get_children():
            item = self.listframe.taskslist.get_children()[0]
        else:
            return
        if forced:
            self.listframe.focus_(item)
            self.update_descr(item)
        else:
            if not self.listframe.taskslist.selection():
                self.listframe.focus_(item)
                self.update_descr(item)
            else:
                self.listframe.taskslist.focus_set()

    def locate_task(self):
        """Search task by keywords."""
        searchword = self.searchentry.get()
        if searchword:
            self.clear_all()
            task_items = []
            if self.ignore_case.get():
                for key in self.tdict:
                    if searchword.lower() in self.tdict[key][1].lower():
                        task_items.append(key)
                    # Need to be sure that there is non-empty description:
                    elif self.tdict[key][3]:
                        if searchword.lower() in self.tdict[key][3].lower():
                            task_items.append(key)
            else:
                for key in self.tdict:
                    if searchword in self.tdict[key][1]:
                        task_items.append(key)
                    elif self.tdict[key][3]:
                        if searchword in self.tdict[key][3]:
                            task_items.append(key)
            if task_items:
                for item in task_items:
                    self.listframe.taskslist.selection_add(item)
                item = self.listframe.taskslist.selection()[0]
                self.listframe.taskslist.see(item)
                self.listframe.taskslist.focus_set()
                self.listframe.taskslist.focus(item)
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
        task_name = self.addentry.get()
        if task_name:
            for x in ('"', "'", "`"):
                task_name = task_name.replace(x, '')
            try:
                self.db.insert_task(task_name)
            except core.DbErrors:
                self.db.reconnect()
                for item in self.tdict:
                    if self.tdict[item][1] == task_name:
                        self.listframe.focus_(item)
                        self.update_descr(item)
                        break
                else:
                    showinfo("Task exists",
                             "Task already exists. "
                             "Change filter configuration to see it.")
            else:
                self.update_list()
                # If created task appears in the table, highlighting it:
                for item in self.tdict:
                    if self.tdict[item][1] == task_name:
                        self.listframe.focus_(item)
                        break
                else:
                    showinfo("Task created",
                             "Task successfully created. "
                             "Change filter configuration to see it.")

    def filter_query(self):
        return self.db.find_by_clause(
            'options', 'name', 'filter', 'value')[0][0]

    def update_list(self):
        """Updating table contents using database query."""
        # Restoring filter value:
        query = self.filter_query()
        if query:
            self.filterbutton.config(bg='lightblue')
            self.db.exec_script(query)
        else:
            self.filterbutton.config(bg=GLOBAL_OPTIONS["colour"])
            self.db.exec_script(self.main_script)
        tlist = self.db.cur.fetchall()
        self.listframe.update_list([[f[1], f[2], f[4]] for f in tlist])
        # Dictionary with row ids and tasks info:
        self.tdict = {}
        i = 0
        for task_id in self.listframe.taskslist.get_children():
            self.tdict[task_id] = tlist[i]
            i += 1
        self.update_descr(None)
        self.update_fulltime()

    def update_fulltime(self):
        """Updates value in "fulltime" frame."""
        self.fulltime = core.time_format(
            sum([self.tdict[x][2] for x in self.tdict]))
        self.fulltime_frame.config(text=self.fulltime)

    def descr_click(self, event):
        """Updates description for the task with item id of the row
        selected by click."""
        pos = self.listframe.taskslist.identify_row(event.y)
        if pos and pos != '#0' and not self.modifier_pressed:
            self.listframe.focus_(pos)
        self.update_descr(self.listframe.taskslist.focus())

    def descr_up(self, event):
        """Updates description for the item id which is BEFORE selected."""
        item = self.listframe.taskslist.focus()
        prev_item = self.listframe.taskslist.prev(item)
        if prev_item == '':
            self.update_descr(item)
        else:
            self.update_descr(prev_item)

    def descr_down(self, event):
        """Updates description for the item id which is AFTER selected."""
        item = self.listframe.taskslist.focus()
        next_item = self.listframe.taskslist.next(item)
        if next_item == '':
            self.update_descr(item)
        else:
            self.update_descr(next_item)

    def update_descr(self, item):
        """Filling task description frame."""
        if item is None:
            self.description.update_text('')
        elif item != '':
            self.description.update_text(self.tdict[item][3])

    def select_all(self):
        self.listframe.taskslist.selection_set(
            self.listframe.taskslist.get_children())

    def clear_all(self):
        self.listframe.taskslist.selection_remove(
            self.listframe.taskslist.get_children())

    def delete(self):
        """Remove selected tasks from the database and the table."""
        ids = [self.tdict[x][0] for x in self.listframe.taskslist.selection()
               if self.tdict[x][0]
               not in GLOBAL_OPTIONS["tasks"]]
        items = [x for x in self.listframe.taskslist.selection() if
                 self.tdict[x][0] in ids]
        if ids:
            answer = askyesno("Warning",
                              "Are you sure you want to delete selected tasks?",
                              parent=self)
            if answer:
                self.db.delete_tasks(tuple(ids))
                self.listframe.taskslist.delete(*items)
                for item in items:
                    self.tdict.pop(item)
                self.update_descr(None)
                self.update_fulltime()

    def edit(self):
        """Show task edit window."""
        item = self.listframe.taskslist.focus()
        try:
            id_name = (self.tdict[item][0], self.tdict[item][
                1])  # Tuple: (selected_task_id, selected_task_name)
        except KeyError:
            pass
        else:
            task_changed = tk.IntVar()
            TaskEditWindow(id_name[0], self, variable=task_changed)
            if task_changed.get() == 1:
                # Reload task information from database:
                new_task_info = self.db.select_task(id_name[0])
                # Update description:
                self.tdict[item] = new_task_info
                self.update_descr(item)
                # Update data in a table:
                self.listframe.taskslist.item(item, values=(
                new_task_info[1], core.time_format(new_task_info[2]),
                new_task_info[4]))
                self.update_fulltime()
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
                       value=operating_mode, table='options', updfiled='name')
        self.db.update('filter', field='value', value=script, table='options',
                       updfiled='name')
        self.db.update('filter_tags', field='value',
                       value=','.join([str(x) for x in tags]), table='options',
                       updfiled='name')
        self.db.update('filter_dates', field='value', value=','.join(dates),
                       table='options', updfiled='name')
        if update != self.filter_query():
            self.update_list()

    def raise_window(self):
        self.grab_set()
        self.lift()


class TaskEditWindow(Window):
    """Task properties window."""

    def __init__(self, taskid, parent=None, variable=None, **options):
        super().__init__(master=parent, **options)
        # Connected with external IntVar.
        # Needed to avoid unnecessary operations in parent window:
        self.change = variable
        # Task information from database:
        self.task = self.db.select_task(taskid)
        # List of dates connected with this task:
        dates = [x[0] + " - " + core.time_format(x[1]) for x in
                 self.db.find_by_clause('activity', 'task_id', '%s' %
                                        taskid, 'date, spent_time', 'date')]
        self.title("Task properties: {}".format(
            self.db.find_by_clause('tasks', 'id', taskid, 'name')[0][0]))
        self.minsize(width=400, height=300)
        elements.SimpleLabel(self, text="Task name:", fontsize=10).grid(
            row=0, column=0, pady=5, padx=5, sticky='w')
        # Frame containing task name:
        TaskLabel(self, width=60, height=1, bg=GLOBAL_OPTIONS["colour"],
                  text=self.task[1],
                  anchor='w').grid(row=1, columnspan=5, sticky='ew', padx=6)
        tk.Frame(self, height=30).grid(row=2)
        elements.SimpleLabel(self, text="Description:", fontsize=10).grid(
            row=3, column=0, pady=5, padx=5, sticky='w')
        # Task description frame. Editable:
        self.description = Description(self, paste_menu=True, width=60,
                                       height=6)
        self.description.config(state='normal', bg='white')
        if self.task[3]:
            self.description.insert(self.task[3])
        self.description.grid(row=4, columnspan=5, sticky='ewns', padx=5)
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
        TaskLabel(self, width=11,
                  text='{}'.format(core.time_format(self.task[2]))).grid(
                            row=6, column=1, pady=5, padx=5, sticky='w')
        elements.SimpleLabel(self, text='Dates:').grid(row=6, column=2,
                                                       sticky='w')
        # Frame containing list of dates connected with current task:
        datlist = Description(self, height=3, width=30)
        datlist.update_text('\n'.join(dates))
        datlist.grid(row=6, column=3, rowspan=3, columnspan=2, sticky='ew',
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
        self.description.text.focus_set()
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
        self.tags = Tagslist(self.db.tags_dict(self.task[0]), self,
                             orientation='horizontal', width=300, height=30)
        self.tags.grid(row=5, column=1, columnspan=3, pady=5, padx=5,
                       sticky='we')

    def update_task(self):
        """Update task in database."""
        taskdata = self.description.get().rstrip()
        self.db.update_task(self.task[0], field='description', value=taskdata)
        # Renew tags list for the task:
        existing_tags = [x[0] for x in
                         self.db.find_by_clause('tasks_tags', 'task_id',
                                                self.task[0], 'tag_id')]
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                if item[0] not in existing_tags:
                    self.db.insert('tasks_tags', ('task_id', 'tag_id'),
                                   (self.task[0], item[0]))
            else:
                self.db.delete(table="tasks_tags", task_id=self.task[0],
                               tag_id=item[0])
        # Reporting to parent window that task has been changed:
        if self.change:
            self.change.set(1)
        self.destroy()


class TagsEditWindow(Window):
    """Checkbuttons editing window.."""

    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.parent = parent
        self.addentry()
        self.tags_update()
        self.closebutton = elements.TaskButton(self, text='Close',
                                               command=self.destroy)
        self.deletebutton = elements.TaskButton(self, text='Delete',
                                                command=self.delete)
        self.maxsize(width=500, height=500)
        self.window_elements_config()
        self.prepare()

    def window_elements_config(self):
        """Window additional parameters configuration."""
        self.title("Tags editor")
        self.minsize(width=300, height=300)
        self.closebutton.grid(row=2, column=2, pady=5, padx=5, sticky='e')
        self.deletebutton.grid(row=2, column=0, pady=5, padx=5, sticky='w')

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


class TimestampsWindow(TagsEditWindow):
    """Window with timestamps for selected task."""

    def __init__(self, taskid, current_task_time, parent=None, **options):
        self.taskid = taskid
        self.current_time = current_task_time
        super().__init__(parent=parent, **options)

    def select_all(self):
        for item in self.tags.states_list:
            item[1][0].set(1)

    def clear_all(self):
        for item in self.tags.states_list:
            item[1][0].set(0)

    def window_elements_config(self):
        """Configure some window parameters."""
        self.title("Timestamps: {}".format(
            self.db.find_by_clause('tasks', 'id', self.taskid, 'name')[0][0]))
        self.minsize(width=400, height=300)
        elements.TaskButton(self, text="Select all",
                            command=self.select_all).grid(row=2, column=0,
                                                          pady=5, padx=5,
                                                          sticky='w')
        elements.TaskButton(self, text="Clear all",
                            command=self.clear_all).grid(row=2, column=2,
                                                         pady=5, padx=5,
                                                         sticky='e')
        tk.Frame(self, height=40).grid(row=3)
        self.closebutton.grid(row=4, column=2, pady=5, padx=5, sticky='w')
        self.deletebutton.grid(row=4, column=0, pady=5, padx=5, sticky='e')

    def addentry(self):
        """Empty method just for suppressing unnecessary element creation."""
        pass

    def tags_get(self):
        """Creates timestamps list."""
        self.tags = Tagslist(
            self.db.timestamps(self.taskid, self.current_time), self,
            width=400, height=300)

    def del_record(self, dellist):
        """Deletes selected timestamps."""
        for x in dellist:
            self.db.delete(table="timestamps", timestamp=x,
                           task_id=self.taskid)


class HelpWindow(Window):
    """Help window."""

    def __init__(self, parent=None, text='', **options):
        super().__init__(master=parent, **options)
        self.title("Help")
        main_frame = tk.Frame(self)
        self.helptext = Description(main_frame, fontsize=13)
        self.helptext.insert(text)
        self.helptext.config(state='disabled')
        self.helptext.grid(row=0, column=0, sticky='news')
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
        self.changed = variable
        # Operating mode of the filter: "AND", "OR".
        self.operating_mode = tk.StringVar()
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
        self.dateslist = Tagslist(
            [[x, [1 if x in stored_dates else 0, x]] for x in dates], self,
            width=200, height=300)
        self.tagslist = Tagslist(tags, self, width=200, height=300)
        self.dateslist.grid(row=1, column=0, pady=5, padx=5, sticky='news')
        self.tagslist.grid(row=1, column=1, pady=5, padx=5, sticky='news')
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
        checkframe = tk.Frame(self)
        checkframe.grid(row=7, columnspan=2, pady=5)
        elements.SimpleRadiobutton(checkframe, text="AND",
                                   variable=self.operating_mode,
                                   value="AND").grid(row=0, column=0,
                                                     sticky='e')
        elements.SimpleRadiobutton(checkframe, text="OR",
                                   variable=self.operating_mode,
                                   value="OR").grid(row=0, column=1,
                                                    sticky='w')
        self.operating_mode.set(
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
        for x in self.dateslist.states_list:
            x[1][0].set(0)

    def clear_tags(self):
        for x in self.tagslist.states_list:
            x[1][0].set(0)

    def select_dates(self):
        """Pops up window where user can select dates interval."""
        start_date = tk.StringVar(self)
        end_date = tk.StringVar(self)
        correct = tk.DoubleVar(self)
        CalendarWindow(self, correct, startvar=start_date, endvar=end_date,
                       startdate=self.dateslist.states_list[-1][0],
                       enddate=self.dateslist.states_list[0][0])
        if correct.get():
            for date in self.dateslist.states_list:
                date[1][0].set(0)
                if core.str_to_date(start_date.get()) <= core.str_to_date(
                        date[0]) <= core.str_to_date(end_date.get()):
                    date[1][0].set(1)

    def apply_filter(self):
        """Create database script based on checkboxes values."""
        dates = list(reversed(
            [x[0] for x in self.dateslist.states_list if x[1][0].get() == 1]))
        tags = list(reversed(
            [x[0] for x in self.tagslist.states_list if x[1][0].get() == 1]))
        if not dates and not tags:
            script = None
            self.operating_mode.set("AND")
        else:
            if self.operating_mode.get() == "OR":
                script = 'SELECT id, name, total_time, description, ' \
                         'creation_date FROM tasks JOIN activity ' \
                         'ON activity.task_id=tasks.id JOIN tasks_tags ' \
                         'ON tasks_tags.task_id=tasks.id ' \
                         'JOIN (SELECT task_id, sum(spent_time) ' \
                         'AS total_time ' \
                         'FROM activity GROUP BY task_id) AS act ' \
                         'ON act.task_id=tasks.id WHERE date IN {1} ' \
                         'OR tag_id IN {0} ' \
                         'GROUP BY act.task_id'.format(
                    "('%s')" % tags[0] if len(tags) == 1 else tuple(tags),
                    "('%s')" % dates[0] if len(dates) == 1 else tuple(dates))
            else:
                if dates and tags:
                    script = 'SELECT DISTINCT id, name, total_time, ' \
                             'description, creation_date FROM tasks  JOIN ' \
                             '(SELECT task_id, sum(spent_time) AS total_time '\
                             'FROM activity WHERE activity.date IN {0} ' \
                             'GROUP BY task_id) AS act ' \
                             'ON act.task_id=tasks.id JOIN (SELECT tt.task_id'\
                             ' FROM tasks_tags AS tt WHERE ' \
                             'tt.tag_id IN {1} GROUP BY tt.task_id ' \
                             'HAVING COUNT(DISTINCT tt.tag_id)={3}) AS x ON ' \
                             'x.task_id=tasks.id JOIN (SELECT act.task_id ' \
                             'FROM activity AS act WHERE act.date IN {0} ' \
                             'GROUP BY act.task_id HAVING ' \
                             'COUNT(DISTINCT act.date)={2}) AS y ON ' \
                             'y.task_id=tasks.id'.format(
                        "('%s')" % dates[0] if len(dates) == 1 else tuple(
                            dates),
                        "('%s')" % tags[0] if len(tags) == 1 else tuple(tags),
                        len(dates), len(tags))
                elif not dates:
                    script = 'SELECT DISTINCT id, name, total_time, ' \
                             'description, creation_date FROM tasks  ' \
                             'JOIN (SELECT task_id, sum(spent_time) ' \
                             'AS total_time FROM activity GROUP BY ' \
                             'task_id) AS act ON act.task_id=tasks.id ' \
                             'JOIN (SELECT tt.task_id FROM tasks_tags ' \
                             'AS tt WHERE tt.tag_id IN {0} GROUP BY ' \
                             'tt.task_id HAVING ' \
                             'COUNT(DISTINCT tt.tag_id)={1}) AS x ON ' \
                             'x.task_id=tasks.id'.format(
                        tuple(tags) if len(tags) > 1 else "(%s)" % tags[0],
                        len(tags))
                elif not tags:
                    script = 'SELECT DISTINCT id, name, total_time, ' \
                             'description, creation_date FROM tasks  ' \
                             'JOIN (SELECT task_id, sum(spent_time) ' \
                             'AS total_time FROM activity WHERE activity.date'\
                             ' IN {0} GROUP BY task_id) AS act ' \
                             'ON act.task_id=tasks.id JOIN (SELECT ' \
                             'act.task_id FROM activity AS act ' \
                             'WHERE act.date IN {0} GROUP BY act.task_id ' \
                             'HAVING COUNT(DISTINCT act.date)={1}) AS y ' \
                             'ON y.task_id=tasks.id'.format(
                        tuple(dates) if len(dates) > 1 else "('%s')" % dates[
                            0],
                        len(dates))
        GLOBAL_OPTIONS["filter_dict"] = {
            'operating_mode': self.operating_mode.get(),
            'script': script,
            'tags': tags,
            'dates': dates
        }
        # Reporting to parent window that filter values have been changed:
        if self.changed:
            self.changed.set(1)
        self.destroy()


class CalendarWindow(Window):
    def __init__(self, parent=None, correct_data=None, startvar=None,
                 endvar=None, startdate=None, enddate=None, **options):
        super().__init__(master=parent, **options)
        self.title("Select dates")
        self.correct_data = correct_data
        self.start = startvar
        self.end = endvar
        self.start_date_entry = sel_cal.Datepicker(
            self, datevar=self.start,
            current_month=core.str_to_date(startdate).month,
            current_year=core.str_to_date(startdate).year)
        self.end_date_entry = sel_cal.Datepicker(
            self, datevar=self.end,
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
            core.str_to_date(self.start.get())
            core.str_to_date(self.end.get())
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
        self.active_frames = []
        self.fill()

    def clear(self):
        """Clear all task frames except with opened tasks."""
        for w in self.content_frame.winfo_children():
            if self.frames_count == int(GLOBAL_OPTIONS[
                                            'timers_count']) \
                    or self.frames_count == len(
                    GLOBAL_OPTIONS["tasks"]):
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
                self.frames_count -= 1
                w.destroy()
            self.active_frames.clear()
            self.fill()

    def frames_refill(self):
        """Reload data in every task frame with data."""
        for w in self.content_frame.winfo_children():
            if hasattr(w, 'task'):
                if w.task:
                    state = w.running
                    w.timer_stop()
                    w.prepare_task(w.db.select_task(w.task_id))
                    if state:
                        w.timer_start()

    def fill(self):
        """Create contents of the main frame."""
        if self.frames_count < int(GLOBAL_OPTIONS['timers_count']):
            row_count = range(
                int(GLOBAL_OPTIONS['timers_count']) - self.frames_count)
            for row_number in row_count:
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
        elif len(GLOBAL_OPTIONS["tasks"]) < self.frames_count > int(
                GLOBAL_OPTIONS['timers_count']):
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
                self.active_frames.append(frame)
                frame.timer_stop()

    def resume_all(self):
        for frame in self.active_frames:
            frame.timer_start()

    def stop_all(self):
        for frame in self.frames:
            if frame.running:
                frame.timer_stop()
        self.active_frames.clear()


class MainMenu(tk.Menu):
    """Main window menu."""

    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        file = tk.Menu(self, tearoff=0)
        file.add_command(label="Options...", command=self.options_window,
                         underline=0)
        file.add_separator()
        file.add_command(label="Exit", command=self.exit, underline=1)
        elements.big_font(file, 10)
        self.add_cascade(label="Main menu", menu=file, underline=0)
        helpmenu = tk.Menu(self, tearoff=0)
        helpmenu.add_command(label="Help...",
                             command=lambda: helpwindow(parent=run,
                                                        text=core.HELP_TEXT))
        helpmenu.add_command(label="About...", command=self.aboutwindow)
        elements.big_font(helpmenu, 10)
        self.add_cascade(label="Help", menu=helpmenu)
        elements.big_font(self, 10)

    def options_window(self):
        """Open options window."""
        # number of main window frames:
        var = tk.IntVar(value=int(GLOBAL_OPTIONS['timers_count']))
        # 'always on top' option:
        ontop = tk.IntVar(value=int(GLOBAL_OPTIONS['always_on_top']))
        # 'compact interface' option
        compact = int(GLOBAL_OPTIONS['compact_interface'])
        compact_iface = tk.IntVar(value=compact)
        # 'save tasks on exit' option:
        save = tk.IntVar(value=int(GLOBAL_OPTIONS['preserve_tasks']))
        # 'show current day in timers' option:
        show_today = tk.IntVar(value=int(GLOBAL_OPTIONS['show_today']))
        toggle = int(GLOBAL_OPTIONS['toggle_tasks'])
        toggler = tk.IntVar(value=toggle)
        params = {}
        accept = tk.BooleanVar()
        Options(run, accept, var, ontop, compact_iface, save, show_today,
                toggler)
        if accept.get():
            try:
                count = var.get()
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
            run.wm_attributes("-topmost", ontop.get())
            # apply value of 'compact interface' option:
            params['compact_interface'] = compact_iface.get()
            if compact != compact_iface.get():
                if compact_iface.get() == 0:
                    run.full_interface()
                elif compact_iface.get() == 1:
                    run.small_interface()
            # apply value of 'save tasks on exit' option:
            params['preserve_tasks'] = save.get()
            # apply value of 'show current day in timers' option:
            params['show_today'] = show_today.get()
            # apply value of 'Allow run only one task at a time' option:
            params['toggle_tasks'] = toggler.get()
            # save all parameters to DB:
            self.change_parameter(params)
            # redraw taskframes if needed:
            run.taskframes.fill()
            run.taskframes.frames_refill()
            # Stop all tasks if exclusive run method has been enabled:
            if int(GLOBAL_OPTIONS["toggle_tasks"]) and int(
                    GLOBAL_OPTIONS["toggle_tasks"]) != toggle:
                GLOBAL_OPTIONS["stopall"] = True
        run.lift()

    def change_parameter(self, paramdict):
        """Change option in the database."""
        db = core.Db()
        for parameter_name in paramdict:
            par = str(paramdict[parameter_name])
            db.update(table='options', field='value', value=par,
                      field_id=parameter_name, updfiled='name')
            GLOBAL_OPTIONS[parameter_name] = par
        db.con.close()

    def aboutwindow(self):
        showinfo("About Tasker",
                 "Tasker {0}.\nCopyright (c) Alexey Kallistov, {1}".format(
                     GLOBAL_OPTIONS['version'],
                     datetime.datetime.strftime(datetime.datetime.now(),
                                                "%Y")))

    def exit(self):
        run.destroy()


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
        counterframe = tk.Frame(self)
        fontsize = 9
        elements.CanvasButton(counterframe, text='<', command=self.decrease,
                              fontsize=fontsize, height=fontsize * 3).grid(
            row=0, column=0)
        elements.SimpleEntry(counterframe, width=3, textvariable=counter,
                             justify='center').grid(row=0, column=1,
                                                    sticky='e')
        elements.CanvasButton(counterframe, text='>', command=self.increase,
                              fontsize=fontsize, height=fontsize * 3).grid(
            row=0, column=2)
        counterframe.grid(row=0, column=1)
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
        self.task_ids = [x[0] for x in data.values()]
        self.operating_mode = tk.IntVar(self)
        elements.SimpleLabel(self, text="Export mode", fontsize=10).grid(
            row=0, column=0, columnspan=2, sticky='ns', pady=5)
        elements.SimpleRadiobutton(self, text="Task-based",
                                   variable=self.operating_mode, value=0).grid(
            row=1, column=0)
        elements.SimpleRadiobutton(self, text="Date-based",
                                   variable=self.operating_mode, value=1).grid(
            row=1, column=1)
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
        if self.operating_mode.get() == 0:
            export_data = self.db.tasks_to_export(self.task_ids)
            prepared_data = [
                'Task,Description,Dates,Time,Summarized working time']
            # Don't try to understand this 'for' loop below
            # if you want to save your mind!
            for key in export_data:
                temp_list = [key, export_data[key][0],
                             export_data[key][1][0][0],
                             export_data[key][1][0][1],
                             export_data[key][2]]
                prepared_data.append(','.join(temp_list))
                if len(export_data[key][1]) > 1:
                    for i in range(1, len(export_data[key][1])):
                        prepared_data.append(','.join(
                            ['', '', export_data[key][1][i][0],
                             export_data[key][1][i][1], '']))
                        i += 1
        else:
            export_data = self.db.dates_to_export(self.task_ids)
            prepared_data = [
                'Date,Tasks,Descriptions,Time,Summarized working time']
            for key in export_data:
                temp_list = [key, export_data[key][0][0][0],
                             export_data[key][0][0][1],
                             export_data[key][0][0][2],
                             export_data[key][1]]
                prepared_data.append(','.join(temp_list))
                if len(export_data[key][0]) > 1:
                    for i in range(1, len(export_data[key][0])):
                        prepared_data.append(','.join(
                            ['', export_data[key][0][i][0],
                             export_data[key][0][i][1],
                             export_data[key][0][i][2], '']))
                        i += 1
        self.export('\n'.join(prepared_data))

    def export(self, data):
        filename = asksaveasfilename(parent=self, defaultextension=".csv",
                                     filetypes=[("All files", "*.*"), (
                                     "Comma-separated texts", "*.csv")])
        if filename:
            core.write_to_disk(filename, data)
        self.destroy()


class MainWindow(tk.Tk):
    def __init__(self, **options):
        super().__init__(**options)
        # Default widget colour:
        GLOBAL_OPTIONS["colour"] = self.cget('bg')
        self.title("Tasker")
        self.minsize(height=75, width=0)
        self.resizable(width=0, height=1)
        main_menu = MainMenu(self)  # Create main menu.
        self.config(menu=main_menu)
        self.taskframes = MainFrame(self)  # Main window content.
        self.taskframes.grid(row=0, columnspan=5)
        self.bind("<Configure>", self.taskframes.reconf_canvas)
        if GLOBAL_OPTIONS["compact_interface"] == "0":
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
        if GLOBAL_OPTIONS['always_on_top'] == '1':
            self.wm_attributes("-topmost", 1)
        self.bind("<Key>", self.hotkeys)
        self.paused = False

    def hotkeys(self, event):
        """Execute corresponding actions for hotkeys."""
        if event.keysym in ('Cyrillic_yeru', 'Cyrillic_YERU', 's', 'S'):
            self.stopall()
        elif event.keysym in ('Cyrillic_es', 'Cyrillic_ES', 'c', 'C'):
            self.taskframes.clear_all()
        elif event.keysym in (
        'Cyrillic_shorti', 'Cyrillic_SHORTI', 'q', 'Q', 'Escape'):
            self.destroy()

    def full_interface(self, firstrun=False):
        """Create elements which are displayed in full interface mode."""
        self.add_frame = tk.Frame(self, height=35)
        self.add_frame.grid(row=1, columnspan=5)
        self.add_stop_button = elements.TaskButton(self, text="Stop all",
                                                   command=self.stopall)
        self.add_stop_button.grid(row=2, column=2, sticky='sn', pady=5, padx=5)
        self.add_clear_button = elements.TaskButton(
            self, text="Clear all",
            command=self.taskframes.clear_all)
        self.add_clear_button.grid(row=2, column=0, sticky='wsn', pady=5,
                                   padx=5)
        self.add_pause_button = elements.TaskButton(self, text="Pause all",
                                                    command=self.pause_all,
                                                    textwidth=10)
        self.add_pause_button.grid(row=2, column=3, sticky='snw', pady=5,
                                   padx=5)
        self.add_quit_button = elements.TaskButton(self, text="Quit",
                                                   command=self.destroy)
        self.add_quit_button.grid(row=2, column=4, sticky='sne', pady=5,
                                  padx=5)
        if not firstrun:
            self.taskframes.change_interface('normal')

    def small_interface(self):
        """Destroy all additional interface elements."""
        for widget in self.add_frame, self.add_stop_button, \
                      self.add_clear_button, self.add_quit_button:
            widget.destroy()
        self.taskframes.change_interface('small')

    def pause_all(self):
        if self.paused:
            self.add_pause_button.config(text="Pause all")
            self.taskframes.resume_all()
            self.paused = False
        else:
            self.add_pause_button.config(text="Resume all")
            self.taskframes.pause_all()
            self.paused = True

    def stopall(self):
        """Stop all running timers."""
        self.taskframes.stop_all()
        self.paused = False
        self.add_pause_button.config(text="Pause all")

    def destroy(self):
        answer = askyesno("Quit confirmation", "Do you really want to quit?")
        if answer:
            db = core.Db()
            if GLOBAL_OPTIONS["preserve_tasks"] == "1":
                tasks = ','.join([str(x) for x in GLOBAL_OPTIONS["tasks"]])
                if int(GLOBAL_OPTIONS['timers_count']) < len(
                        GLOBAL_OPTIONS["tasks"]):
                    db.update(table='options', field='value',
                              value=len(GLOBAL_OPTIONS["tasks"]),
                              field_id='timers_count', updfiled='name')
            else:
                tasks = ''
            db.update(table='options', field='value', value=tasks,
                      field_id='tasks', updfiled='name')
            db.con.close()
            super().destroy()


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
    # Interval between saving time to database:
    SAVE_INTERVAL = 10000  # ms
    # Check if tasks database actually exists:
    core.check_database()
    # Create options dictionary:
    GLOBAL_OPTIONS = get_options()
    # Global tasks ids set. Used for preserve duplicates:
    if GLOBAL_OPTIONS["tasks"]:
        GLOBAL_OPTIONS["tasks"] = dict.fromkeys(
            [int(x) for x in GLOBAL_OPTIONS["tasks"].split(",")], False)
    else:
        GLOBAL_OPTIONS["tasks"] = dict()
    # List of preserved tasks which are not open:
    GLOBAL_OPTIONS["preserved_tasks_list"] = list(GLOBAL_OPTIONS["tasks"])
    # Widget which is currently connected to context menu:
    GLOBAL_OPTIONS["selected_widget"] = None
    GLOBAL_OPTIONS.update(
        {"MAX_TASKS": MAX_TASKS, "SAVE_INTERVAL": SAVE_INTERVAL})

    # Main window:
    run = MainWindow()
    run.mainloop()
