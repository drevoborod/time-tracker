#!/usr/bin/env python3

import time

import tkinter.font as fonter
import tkinter as tk
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import askyesno, showinfo
from tkinter import ttk

import core


class BindedWidget(tk.Widget):
    """Frame with changed .bind() method. I applies recursive to all widget's children."""
    def bind(self, sequence=None, func=None, add=None):
        if not isinstance(self, tk.Menu):
            tk.Misc.bind(self, sequence, func, add)
        for child in self.winfo_children():
            BindedWidget.bind(child, sequence, func, add)


class TaskFrame(tk.Frame):
    """Task frame on application's main screen."""
    def __init__(self, parent=None):
        super().__init__(parent, relief='groove', bd=2)
        self.db = core.Db()
        self.create_content()

    def create_content(self):
        """Creates all window elements."""
        self.startstopvar = tk.StringVar()     # Text on "Start" button.
        self.startstopvar.set("Start")
        self.task = None       # Fake name of running task (which actually is not selected yet).
        l1 = tk.Label(self, text='Task name:')
        big_font(l1, size=12)
        l1.grid(row=0, column=1, columnspan=3)
        # Task name field:
        self.tasklabel = TaskLabel(self, width=50, anchor='w')
        big_font(self.tasklabel, size=14)
        self.tasklabel.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky='w')
        self.openbutton = TaskButton(self, text="Task...", command=self.name_dialogue)
        self.openbutton.grid(row=1, column=5, padx=5, pady=5, sticky='e')
        # Task description field:
        self.description = Description(self, width=60, height=3)
        self.description.grid(row=2, column=0, columnspan=6, padx=5, pady=6, sticky='we')
        self.startbutton = TaskButton(self, state='disabled', command=self.startstopbutton, textvariable=self.startstopvar)
        big_font(self.startbutton, size=14)
        self.startbutton.grid(row=3, column=0, sticky='wsn', padx=5)
        # Counter frame:
        self.timer_window = TaskLabel(self, width=10, state='disabled')
        big_font(self.timer_window)
        self.timer_window.grid(row=3, column=1, pady=5)
        self.add_timestamp_button = TaskButton(self, text='Add\ntimestamp', width=10, state='disabled', command=self.add_timestamp)
        self.add_timestamp_button.grid(row=3, column=2, sticky='w', padx=5)
        self.timestamps_window_button = TaskButton(self, text='View\ntimestamps', width=10, state='disabled', command=self.timestamps_window)
        self.timestamps_window_button.grid(row=3, column=3, sticky='w', padx=5)
        self.properties = TaskButton(self, text="Properties", width=10, state='disabled', command=self.properties_window)
        self.properties.grid(row=3, column=4, sticky='e', padx=5)
        self.clearbutton = TaskButton(self, text="Clear", state='disabled', command=self.clear)  # Clear frame button.
        self.clearbutton.grid(row=3, column=5, sticky='e', padx=5)
        self.start_time = 0     # Starting value of the counter.
        self.running_time = 0   # Current value of the counter.
        self.running = False

    def timestamps_window(self):
        """Timestamps window opening."""
        TimestampsWindow(self.task_id, self.running_time, self)

    def add_timestamp(self):
        """Adding timestamp to database."""
        self.db.insert('timestamps', ('task_id', 'timestamp'), (self.task_id, self.running_time))
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
        self.editwindow = TaskEditWindow(self.task[0], self, variable=edited)
        if edited.get() == 1:
            self.update_description()

    def clear(self):
        """Recreation of frame contents."""
        self.timer_stop()
        for w in self.winfo_children():
            w.destroy()
        core.Params.tasks.remove(self.task[0])
        self.create_content()

    def name_dialogue(self):
        """Task selection window."""
        self.dialogue_window = TaskSelectionWindow(self)
        TaskButton(self.dialogue_window, text="Open", command=self.get_task_name).grid(row=5, column=0, padx=5, pady=5, sticky='w')
        TaskButton(self.dialogue_window, text="Cancel", command=self.dialogue_window.destroy).grid(row=5, column=4, padx=5, pady=5, sticky='e')
        self.dialogue_window.listframe.taskslist.bind("<Return>", lambda event: self.get_task_name())
        self.dialogue_window.listframe.taskslist.bind("<Double-1>", lambda event: self.get_task_name())

    def get_task_name(self):
        """Getting selected task's name."""
        # List of selected tasks item id's:
        tasks = self.dialogue_window.listframe.taskslist.selection()
        if tasks:
            self.task_id = self.dialogue_window.tdict[tasks[0]][0]
            # Task parameters from database:
            task = self.db.find_by_clause("tasks", "id", self.task_id, "*")[0]
            # Checking if task is already open in another frame:
            if self.task_id not in core.Params.tasks:
                # Checking if there is open task in this frame:
                if self.task:
                    # If it is, we remove it from running tasks set:
                    core.Params.tasks.remove(self.task[0])
                    # Stopping current timer and saving its state:
                    self.timer_stop()
                # Preparing new task:
                self.prepare_task(task)
            else:
                # If selected task is already open in another frame, just closing window:
                self.dialogue_window.destroy()

    def prepare_task(self, task):
        """Prepares frame elements to work with."""
        # Adding task id to set of running tasks:
        core.Params.tasks.add(task[0])
        self.task = list(task)
        # Taking current counter value from database:
        self.running_time = self.task[2]
        self.timer_window.config(text=core.time_format(self.running_time))
        self.dialogue_window.destroy()      # Close task selection window.
        self.tasklabel.config(text=self.task[1])
        self.startbutton.config(state='normal')
        self.properties.config(state='normal')
        self.clearbutton.config(state='normal')
        self.timer_window.config(state='normal')
        self.add_timestamp_button.config(state='normal')
        self.timestamps_window_button.config(state='normal')
        self.description.update_text(self.task[3])

    def timer_update(self, counter=0):
        """Renewal of the counter."""
        interval = 250      # Time interval in milliseconds before next iteration of recursion.
        self.running_time = time.time() - self.start_time
        self.timer_window.config(text=core.time_format(self.running_time))
        # Checking if "Stop all" button is pressed:
        if not core.Params.stopall:
            # Every minute counter value is saved in database:
            if counter >= 60000:
                self.db.update_task(self.task[0], value=self.running_time)
                counter = 0
            else:
                counter += interval
            # self.timer variable becomes ID created by after():
            self.timer = self.timer_window.after(250, self.timer_update, counter)
        else:
            self.timer_stop()

    def timer_start(self):
        """Counter start."""
        if not self.running:
            core.Params.stopall = False
            # Setting current counter value:
            self.start_time = time.time() - self.task[2]
            self.timer_update()
            self.running = True
            self.startstopvar.set("Stop")

    def timer_stop(self):
        """Stop counter and save its value to database."""
        if self.running:
            # after_cancel() stops execution of callback with given ID.
            self.timer_window.after_cancel(self.timer)
            self.running_time = time.time() - self.start_time
            self.running = False
            self.start_time = 0
            # Writing value into database:
            self.db.update_task(self.task[0], value=self.running_time)
            self.task[2] = self.running_time
            self.startstopvar.set("Start")
            self.update_description()

    def update_description(self):
        """Update text in "Description" field."""
        self.task[3] = self.db.find_by_clause("tasks", "id", self.task[0], "description")[0][0]
        self.description.update_text(self.task[3])

    def destroy(self):
        """Closes frame and writes counter value into database."""
        self.timer_stop()
        tk.Frame.destroy(self)


class TaskLabel(tk.Label):
    """Simple sunken text label."""
    def __init__(self, parent, anchor='center', **kwargs):
        super().__init__(master=parent, relief='sunken', anchor=anchor, **kwargs)
        context_menu = RightclickMenu()
        self.bind("<Button-3>", context_menu.context_menu_show)


class TaskButton(tk.Button):
    """Just a button with some default parameters."""
    def __init__(self, parent, width=8, **kwargs):
        super().__init__(master=parent, width=width, **kwargs)


class TaskList(tk.Frame):
    """Scrollable tasks table."""
    def __init__(self, columns, parent=None, **options):
        super().__init__(master=parent, **options)
        self.taskslist = ttk.Treeview(self, takefocus=1)     # A table.
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.taskslist.yview)
        self.taskslist.config(yscrollcommand=scroller.set)
        scroller.pack(side='right', fill='y')
        self.taskslist.pack(fill='both', expand=1)
        # Creating and naming columns:
        self.taskslist.config(columns=tuple([col[0] for col in columns]))
        for index, col in enumerate(columns):
            # Configuring columns with given ids:
            self.taskslist.column(columns[index][0], width=100, minwidth=100, anchor='center')
            # Configuring headers of columns with given ids:
            self.taskslist.heading(columns[index][0], text=columns[index][1], command=lambda c=columns[index][0]: self.sortlist(c, True))
        self.taskslist.column('#0', anchor='w', width=70, minwidth=50, stretch=0)
        self.taskslist.column('taskname', width=600, anchor='w')

    def sortlist(self, col, reverse):
        """Sorting by click on column header."""
        # set(ID, column) returns name of every record in the column.
        l = [(self.taskslist.set(k, col), k) for k in self.taskslist.get_children()]
        l.sort(reverse=reverse)
        for index, value in enumerate(l):
            self.taskslist.move(value[1], '', index)
        self.taskslist.heading(col, command=lambda: self.sortlist(col, not reverse))

    def insert_tasks(self, tasks):
        # Insert rows in the table. Row contents are tuples given in values=.
        for i, v in enumerate(tasks):
            self.taskslist.insert('', i, text="#%d" % (i + 1), values=v)      # item, number, value

    def update_list(self, tasks):
        for item in self.taskslist.get_children():
            self.taskslist.delete(item)
        self.insert_tasks(tasks)

    def focus_(self, item):
        """Focuses on the row with given id."""
        self.taskslist.see(item)
        self.taskslist.selection_set(item)
        self.taskslist.focus_set()
        self.taskslist.focus(item)


class TaskSelectionWindow(tk.Toplevel):
    """Task selection and creation window."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.db = core.Db()
        self.title("Task selection")
        self.minsize(width=450, height=300)
        self.grab_set()
        tk.Label(self, text="New task:").grid(row=0, column=0, sticky='w', pady=5, padx=5)
        # New task entry field:
        self.addentry = tk.Entry(self, width=50)
        self.addentry.grid(row=0, column=1, columnspan=3, sticky='we')
        # Enter adds new task:
        self.addentry.bind('<Return>', lambda event: self.add_new_task())
        self.addentry.focus_set()
        # "Add task" button:
        self.addbutton = tk.Button(self, text="Add task", command=self.add_new_task, takefocus=0)
        self.addbutton.grid(row=0, column=4, sticky='e', padx=6, pady=5)
        columnnames = [('taskname', 'Task name'), ('time', 'Spent time'), ('date', 'Creation date')]
        # Scrollable tasks table:
        self.listframe = TaskList(columnnames, self)
        self.listframe.grid(row=1, column=0, columnspan=5, pady=10, sticky='news')
        tk.Label(self, text="Summary time:").grid(row=2, column=0, pady=5, padx=5, sticky='w')
        # Summarized time of all tasks in the table:
        self.fulltime_frame = TaskLabel(self, width=13, anchor='center')
        self.fulltime_frame.grid(row=2, column=1, padx=6, pady=5, sticky='e')
        # Selected task description:
        self.description = Description(self, height=4)
        self.description.grid(row=2, column=2, rowspan=2, pady=5, padx=5, sticky='news')
        # "Select all" button:
        selbutton = TaskButton(self, text="Select all...", width=10, command=self.select_all)
        selbutton.grid(row=3, column=0, sticky='w', padx=5, pady=5)
        # "Clear all" button:
        clearbutton = TaskButton(self, text="Clear all...", width=10, command=self.clear_all)
        clearbutton.grid(row=3, column=1, sticky='e', padx=5, pady=5)
        # Task properties button:
        self.editbutton = TaskButton(self, text="Properties", width=10, command=self.edit)
        self.editbutton.grid(row=2, column=3, sticky='w', padx=5, pady=5)
        # Remove task button:
        self.delbutton = TaskButton(self, text="Remove", width=10, command=self.delete)
        self.delbutton.grid(row=3, column=3, sticky='w', padx=5, pady=5)
        # Export button:
        self.exportbutton = TaskButton(self, text="Export...", command=self.export)
        self.exportbutton.grid(row=3, column=4, padx=5, pady=5, sticky='e')
        # Filter button:
        self.filterbutton = TaskButton(self, text="Filter...", command=self.filterwindow)
        self.filterbutton.grid(row=2, column=4, padx=5, pady=5, sticky='e')
        tk.Frame(self, height=40).grid(row=4, columnspan=5, sticky='news')
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.update_list()      # Fill table contents.
        self.current_task = ''      # Current selected task.
        self.listframe.taskslist.bind("<Down>", self.descr_down)
        self.listframe.taskslist.bind("<Up>", self.descr_up)
        self.listframe.taskslist.bind("<Button-1>", self.descr_click)
        self.addentry.bind("<Tab>", lambda e: self.focus_first_item())

    def focus_first_item(self):
        """Selects first item in the table."""
        item = self.listframe.taskslist.get_children()[0]
        self.listframe.focus_(item)
        self.update_descr(item)

    def export(self):
        """Export all tasks from the table into the file."""
        text = '\n'.join(("Task name,Time spent,Creation date",
                          '\n'.join(','.join([row[1], core.time_format(row[2]),
                                              row[4]]) for row in self.tdict.values()),
                          "Summary time,%s" % self.fulltime))
        filename = asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("All files", "*.*"), ("Comma-separated texts", "*.csv")])
        if filename:
            core.export(filename, text)
        # ToDo: Fix: In Windows, two same extensions are added by default.

    def add_new_task(self):
        """Adds new task into the database."""
        task_name = self.addentry.get()
        if task_name:
            try:
                self.db.insert_task(task_name)
            except core.DbErrors:
                pass
            else:
                self.update_list()
                items = {x: self.listframe.taskslist.item(x) for x in self.listframe.taskslist.get_children()}
                # If created task appears in the table, highlighting it:
                for item in items:
                    if items[item]['values'][0] == task_name:
                        self.listframe.focus_(item)
                        break

    def update_list(self):
        """Updating table contents using database query."""
        # Restoring filter value:
        query = self.db.find_by_clause('options', 'option_name', 'filter', 'value')[0][0]
        if query:
            self.db.exec_script(query)
            tlist = self.db.cur.fetchall()
            self.filterbutton.config(bg='lightblue')
        else:
            tlist = self.db.find_all("tasks")
            self.filterbutton.config(bg=core.Params.colour)
        self.listframe.update_list([(f[1], core.time_format(f[2]), f[4]) for f in tlist])
        # Dictionary with row ids and tasks info:
        self.tdict = {}
        i = 0
        for task_id in self.listframe.taskslist.get_children():
            self.tdict[task_id] = tlist[i]
            i += 1
        self.update_fulltime()

    def update_fulltime(self):
        """Updates value in "fulltime" frame."""
        self.fulltime = core.time_format(sum([self.tdict[x][2] for x in self.tdict]))
        self.fulltime_frame.config(text=self.fulltime)

    def descr_click(self, event):
        """Updates description for the task with item id of the row selected by click."""
        self.update_descr(self.listframe.taskslist.identify_row(event.y))

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
        if item != '':
            self.description.update_text(self.tdict[item][3])

    def select_all(self):
        self.listframe.taskslist.selection_set(self.listframe.taskslist.get_children())

    def clear_all(self):
        self.listframe.taskslist.selection_remove(self.listframe.taskslist.get_children())

    def delete(self):
        """Remove selected tasks from the database and the table."""
        ids = [self.tdict[x][0] for x in self.listframe.taskslist.selection() if self.tdict[x][0] not in core.Params.tasks]
        if ids:
            answer = askyesno("Warning", "Are you sure you want to delete selected tasks?", parent=self)
            if answer:
                self.db.delete_tasks(tuple(ids))
                self.update_list()
        self.grab_set()

    def edit(self):
        """Show task edit window."""
        item = self.listframe.taskslist.focus()
        try:
            id_name = (self.tdict[item][0], self.tdict[item][1])  # Tuple: (selected_task_id, selected_task_name)
        except KeyError:
            pass
        else:
            task_changed = tk.IntVar()
            TaskEditWindow(id_name[0], self, variable=task_changed)
            if task_changed.get() == 1:
                # Reload task information from database:
                new_task_info = self.db.find_by_clause("tasks", "id", id_name[0], "*")[0]
                # Update description:
                self.tdict[item] = new_task_info
                self.update_descr(item)
                # Update data in a table:
                self.listframe.taskslist.item(item, values=(new_task_info[1], core.time_format(new_task_info[2]), new_task_info[4]))
                self.update_fulltime()
        self.grab_set()

    def filterwindow(self):
        """Open filters window."""
        filter_changed = tk.IntVar()
        self.filteroptions = FilterWindow(self, variable=filter_changed)
        # Update tasks list only if filter parameters have been changed:
        if filter_changed.get() == 1:
            self.update_list()
        self.grab_set()


class TaskEditWindow(tk.Toplevel):
    """Task properties window."""
    def __init__(self, taskid, parent=None, variable=None, **options):
        super().__init__(master=parent, **options)
        # Connected with external IntVar. Needed to avoid unnecessary operations in parent window:
        self.change = variable
        self.db = core.Db()
        # Task information from database:
        self.task = self.db.find_by_clause("tasks", "id", taskid, "*")[0]
        # List of dates connected with this task:
        dates = [x[0] for x in self.db.find_by_clause("dates", "task_id", taskid, "date")]
        self.grab_set()
        self.title("Task properties")
        self.minsize(width=400, height=300)
        taskname_label = tk.Label(self, text="Task name:")
        big_font(taskname_label, 10)
        taskname_label.grid(row=0, column=0, pady=5, padx=5, sticky='w')
        # Frame containing task name:
        taskname = TaskLabel(self, width=60, height=1, bg=core.Params.colour, text=self.task[1], anchor='w')
        big_font(taskname, 9)
        taskname.grid(row=1, columnspan=5, sticky='ew', padx=6)
        tk.Frame(self, height=30).grid(row=2)
        description = tk.Label(self, text="Description:")
        big_font(description, 10)
        description.grid(row=3, column=0, pady=5, padx=5, sticky='w')
        # Task description frame. Editable:
        self.description = Description(self, width=60, height=6)
        self.description.config(state='normal', bg='white')
        if self.task[3]:
            self.description.insert(self.task[3])
        # Additional command for context menu:
        self.description.context_menu.add_command(label="Paste", command=self.paste_description)
        self.description.grid(row=4, columnspan=5, sticky='ewns', padx=5)
        #
        tk.Label(self, text='Tags:').grid(row=5, column=0, pady=5, padx=5, sticky='nw')
        # Place tags list:
        self.tags_update()
        TaskButton(self, text='Edit tags', width=10, command=self.tags_edit).grid(row=5, column=4, padx=5, pady=5, sticky='e')
        tk.Label(self, text='Time spent:').grid(row=6, column=0, padx=5, pady=5, sticky='w')
        # Frame containing time:
        TaskLabel(self, width=11, text='{}'.format(core.time_format(self.task[2]))).grid(row=6, column=1,
                                                                                         pady=5, padx=5, sticky='w')
        tk.Label(self, text='Dates:').grid(row=6, column=2, sticky='w')
        # Frame containing list of dates connected with current task:
        datlist = Description(self, height=3, width=30)
        datlist.update_text(', '.join(dates))
        datlist.grid(row=6, column=3, rowspan=3, columnspan=2, sticky='ew', padx=5, pady=5)
        #
        tk.Frame(self, height=40).grid(row=9)
        TaskButton(self, text='Ok', command=self.update_task).grid(row=10, column=0, sticky='sw', padx=5, pady=5)   # При нажатии на эту кнопку происходит обновление данных в БД.
        TaskButton(self, text='Cancel', command=self.destroy).grid(row=10, column=4, sticky='se', padx=5, pady=5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=10)
        self.grid_rowconfigure(4, weight=1)
        self.description.text.focus_set()
        self.wait_window()

    def paste_description(self):
        """Insert text from clipboard to a description field."""
        self.description.insert(self.clipboard_get())

    def tags_edit(self):
        """Open tags editor window."""
        TagsEditWindow(self)
        self.tags_update()
        self.grab_set()

    def tags_update(self):
        """Tags list placing."""
        # Tags list. Tags state are saved to database:
        self.tags = Tagslist(self.db.tags_dict(self.task[0]), self, orientation='horizontal', width=300, height=30)
        self.tags.grid(row=5, column=1, columnspan=3, pady=5, padx=5, sticky='we')

    def update_task(self):
        """Update task in database."""
        taskdata = self.description.get().rstrip()
        self.db.update(self.task[0], field='description', value=taskdata)
        # Renew tags list for the task:
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                self.db.insert('tags', ('task_id', 'tag_id'), (self.task[0], item[0]))
            else:
                self.db.exec_script('delete from tags where task_id={0} and tag_id={1}'.format(self.task[0], item[0]))
        # Reporting to parent window that task has been changed:
        if self.change:
            self.change.set(1)
        self.destroy()


class TagsEditWindow(tk.Toplevel):
    """Checkbuttons editing window.."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        self.db = core.Db()
        self.grab_set()
        self.addentry()
        self.tags_update()
        self.closebutton = TaskButton(self, text='Close', command=self.destroy)
        self.deletebutton = TaskButton(self, text='Delete', command=self.delete)
        self.closebutton.grid(row=2, column=0, pady=5, padx=5, sticky='w')
        self.deletebutton.grid(row=2, column=2, pady=5, padx=5, sticky='e')
        self.window_elements_config()
        self.wait_window()

    def window_elements_config(self):
        """Window additional parameters configuration."""
        self.title("Tags editor")
        self.minsize(width=300, height=300)

    def addentry(self):
        """New element addition field"""
        self.addentry_label = tk.Label(self, text="Add tag:")
        self.addentry_label.grid(row=0, column=0, pady=5, padx=5, sticky='w')
        TaskButton(self, text='Add', command=self.add).grid(row=0, column=2, pady=5, padx=5, sticky='e')
        self.addfield = tk.Entry(self, width=20)
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
                pass
            else:
                self.tags_update()

    def delete(self):
        """Remove selected elements from database."""
        dellist = []
        for item in self.tags.states_list:
            if item[1][0].get() == 1:
                dellist.append(item[0])
        if dellist:
            answer = askyesno("Really delete?", "Are you sure you want to delete selected items?", parent=self)
            if answer:
                self.del_record(dellist)
                self.tags_update()

    def tags_get(self):
        self.tags = Tagslist(self.db.simple_tagslist(), self, width=300, height=300)

    def add_record(self, tagname):
        self.db.insert('tagnames', ('tag_id', 'tag_name'), (None, tagname))

    def del_record(self, dellist):
        self.db.delete(tuple(dellist), field='tag_id', table='tagnames')


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
        self.title("Timestamps")
        self.minsize(width=400, height=300)
        TaskButton(self, text="Select all", command=self.select_all).grid(row=2, column=0, pady=5, padx=5, sticky='w')
        TaskButton(self, text="Clear all", command=self.clear_all).grid(row=2, column=2, pady=5, padx=5, sticky='e')
        tk.Frame(self, height=40).grid(row=3)
        self.closebutton.grid(row=4, column=0, pady=5, padx=5, sticky='w')
        self.deletebutton.grid(row=4, column=2, pady=5, padx=5, sticky='e')

    def addentry(self):
        """Empty method just for suppressing unnecessary element creation."""
        pass

    def tags_get(self):
        """Creates timestamps list."""
        self.tags = Tagslist(self.db.timestamps(self.taskid, self.current_time), self, width=400, height=300)

    def del_record(self, dellist):
        """Deletes selected timestamps."""
        for x in dellist:
            self.db.exec_script('delete from timestamps where timestamp={0} and task_id={1}'.format(x, self.taskid))


class HelpWindow(tk.Toplevel):
    """Help window."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, **options)
        main_frame = tk.Frame(self)
        self.helptext = tk.Text(main_frame, wrap='word')
        scroll = tk.Scrollbar(main_frame, command=self.helptext.yview)
        self.helptext.config(yscrollcommand=scroll.set)
        self.helptext.insert(1.0, core.HELP_TEXT)
        self.helptext.config(state='disabled')
        scroll.grid(row=0, column=1, sticky='ns')
        self.helptext.grid(row=0, column=0, sticky='news')
        main_frame.grid(row=0, column=0, sticky='news', padx=5, pady=5)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        TaskButton(self, text='ОК', command=self.destroy).grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)


class Description(tk.Frame):
    """Description frame - Text frame with scroll."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent)
        self.text = tk.Text(self, bg=core.Params.colour, state='disabled', wrap='word', **options)
        scroller = tk.Scrollbar(self)
        scroller.config(command=self.text.yview)
        self.text.config(yscrollcommand=scroller.set)
        scroller.grid(row=0, column=1, sticky='ns')
        self.text.grid(row=0, column=0, sticky='news')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure('all', weight=1)
        # Context menu for copying contents:
        self.context_menu = RightclickMenu()
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


class ScrolledCanvas(tk.Frame):
    """Scrollable Canvas. Scroll may be horizontal or vertical."""
    def __init__(self, parent=None, orientation="vertical", **options):
        super().__init__(master=parent, relief='groove', bd=2)
        scroller = tk.Scrollbar(self, orient=orientation)
        self.canvbox = tk.Canvas(self, **options)
        scroller.config(command=(self.canvbox.xview if orientation == "horizontal" else self.canvbox.yview))
        if orientation == "horizontal":
            self.canvbox.config(xscrollcommand=scroller.set)
        else:
            self.canvbox.config(yscrollcommand=scroller.set)
        scroller.pack(fill='x' if orientation == 'horizontal' else 'y', expand=1,
                      side='bottom' if orientation == 'horizontal' else 'right',
                      anchor='s' if orientation == 'horizontal' else 'e')
        self.content_frame = tk.Frame(self.canvbox)
        self.canvbox.create_window((0, 0), window=self.content_frame, anchor='nw')
        self.content_frame.bind("<Configure>", self.reconf_canvas)
        self.canvbox.pack(fill="x" if orientation == "horizontal" else "both", expand=1)

    def reconf_canvas(self, event):
        """Resizing of canvas scrollable region."""
        self.canvbox.configure(scrollregion=self.canvbox.bbox('all'))


class Tagslist(ScrolledCanvas):
    """Tags list. Accepts tagslist: [[tag_id, [state, 'tagname']]], can be 0 or 1."""
    def __init__(self, tagslist, parent=None, orientation="vertical", **options):
        super().__init__(parent=parent, orientation=orientation, **options)
        self.states_list = tagslist
        for item in self.states_list:
            # Saving tag state:
            state = item[1][0]
            # Inserting dynamic variable instead of the state:
            item[1][0] = tk.IntVar()
            # Connecting new checkbox with this dynamic variable:
            # Добавляем к набору выключателей ещё один и связываем его с динамической переменной:
            cb = tk.Checkbutton(self.content_frame, text=item[1][1], variable=item[1][0])
            cb.pack(side=('left' if orientation == "horizontal" else 'bottom'), anchor='w')
            # Setting dynamic variable value to previously saved state:
            item[1][0].set(state)


class FilterWindow(tk.Toplevel):
    """Filters window."""
    def __init__(self, parent=None, variable=None, **options):
        super().__init__(master=parent, **options)
        self.db = core.Db()
        self.changed = variable     # IntVar instance: used to set 1 if some changes were made. For optimization.
        # Lists of stored filter parameters:
        stored_dates = self.db.find_by_clause('options', 'option_name', 'filter_dates', 'value')[0][0].split(',')
        stored_tags = self.db.find_by_clause('options', 'option_name', 'filter_tags', 'value')[0][0].split(',')
        if stored_tags[0]:      # stored_tags[0] is string.
            stored_tags = [int(x) for x in stored_tags]
        # Dates list:
        self.db.exec_script('select distinct date from dates order by date desc')
        dates = [x[0] for x in self.db.cur.fetchall()]
        # Tags list:
        tags = self.db.simple_tagslist()
        # Checking checkboxes according to their values loaded from database:
        for tag in tags:
            if tag[0] in stored_tags:
                tag[1][0] = 1
        tk.Label(self, text="Dates").grid(row=0, column=0, sticky='n')
        tk.Label(self, text="Tags").grid(row=0, column=1, sticky='n')
        self.dateslist = Tagslist([[x, [1 if x in stored_dates else 0, x]] for x in dates], self, width=200, height=300)
        self.tagslist = Tagslist(tags, self, width=200, height=300)
        self.dateslist.grid(row=1, column=0, pady=5, padx=5, sticky='news')
        self.tagslist.grid(row=1, column=1, pady=5, padx=5, sticky='news')
        TaskButton(self, text="Clear", command=self.clear_dates).grid(row=2, column=0, pady=7, padx=5, sticky='n')
        TaskButton(self, text="Clear", command=self.clear_tags).grid(row=2, column=1, pady=7, padx=5, sticky='n')
        tk.Frame(self, height=40).grid(row=3, column=0, columnspan=2, sticky='news')
        TaskButton(self, text="Cancel", command=self.destroy).grid(row=4, column=1, pady=5, padx=5, sticky='e')
        TaskButton(self, text='Ok', command=self.apply_filter).grid(row=4, column=0, pady=5, padx=5, sticky='w')
        self.minsize(height=250, width=350)
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
        """Create database script based on checkboxes values."""
        dates = list(reversed([x[0] for x in self.dateslist.states_list if x[1][0].get() == 1]))
        tags = list(reversed([x[0] for x in self.tagslist.states_list if x[1][0].get() == 1]))
        if not dates and not tags:
            script = None
        else:
            if dates and tags:
                script = "select distinct taskstable.* from tasks as taskstable join tags as tagstable on taskstable.id = tagstable.task_id " \
                        "join dates as datestable on taskstable.id = datestable.task_id where tagstable.tag_id in {0} "\
                        "and datestable.date in {1}".format(tuple(tags) if len(tags) > 1 else "(%s)" % tags[0],
                                                            tuple(dates) if len(dates) > 1 else "('%s')" % dates[0])
            elif not dates:
                script = "select distinct taskstable.* from tasks as taskstable join tags as tagstable on taskstable.id = tagstable.task_id " \
                        "where tagstable.tag_id in {0}".format(tuple(tags) if len(tags) > 1 else "(%s)" % tags[0])
            elif not tags:
                script = "select distinct taskstable.* from tasks as taskstable join dates as datestable on taskstable.id = "\
                        "datestable.task_id where datestable.date in {0}".format(tuple(dates) if len(dates) > 1 else "('%s')" % dates[0])
        self.db.update('filter', field='value', value=script, table='options', updfiled='option_name')
        self.db.update('filter_tags', field='value', value=','.join([str(x) for x in tags]), table='options', updfiled='option_name')
        self.db.update('filter_dates', field='value', value=','.join(dates), table='options', updfiled='option_name')
        # Reporting to parent window that filter values have been changed:
        if self.changed:
            self.changed.set(1)
        self.destroy()


class RightclickMenu(tk.Menu):
    """Popup menu. By default has one menuitem - "copy"."""
    def __init__(self, parent=None, **options):
        super().__init__(master=parent, tearoff=0, **options)
        self.add_command(label="Copy", command=copy_to_clipboard)

    def context_menu_show(self, event):
        """Function links context menu with current selected widget and pops menu up."""
        self.post(event.x_root, event.y_root)
        core.Params.selected_widget = event.widget

def big_font(unit, size=20):
    """Font size of a given unit increase."""
    fontname = fonter.Font(font=unit['font']).actual()['family']
    unit.config(font=(fontname, size))


def helpwindow():
    HelpWindow(run)


def copy_to_clipboard():
    """Copy widget text to clipboard."""
    core.Params.selected_widget.clipboard_clear()
    if isinstance(core.Params.selected_widget, tk.Text):
        core.Params.selected_widget.clipboard_append(core.Params.selected_widget.get(1.0, 'end'))
    else:
        core.Params.selected_widget.clipboard_append(core.Params.selected_widget.cget("text"))


def stopall():
    core.Params.stopall = True


def quit():
    answer = askyesno("Quit confirmation", "Do you really want to quit?")
    if answer:
        run.destroy()


# Quantity of task frames on main screen:
TASKFRAMES_COUNT = 3
# Check if tasks database actually exists:
core.check_database()
# Global tasks ids set. Used for preserve duplicates:
core.Params.tasks = set()
# If True, all running timers will be stopped:
core.Params.stopall = False
# Widget which is currently connected to context menu:
core.Params.selected_widget = None

# Main window:
run = tk.Tk()
# Default widget colour:
core.Params.colour = run.cget('bg')
run.title("Tasker")
run.resizable(width=0, height=0)
for row_number in list(range(TASKFRAMES_COUNT)):
    TaskFrame(parent=run).grid(row=row_number, pady=5, padx=5, ipady=3, columnspan=5)
    tk.Frame(run, height=15).grid(row=row_number+1)
TaskButton(run, text="Help", command=helpwindow).grid(row=row_number+2, column=0, sticky='sw', pady=5, padx=5)
TaskButton(run, text="Stop all", command=stopall).grid(row=row_number+2, column=2, sticky='sn', pady=5, padx=5)
TaskButton(run, text="Quit", command=quit).grid(row=row_number+2, column=4, sticky='se', pady=5, padx=5)
run.mainloop()

