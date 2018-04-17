#!/usr/bin/env python3

import tkinter as tk


class Text(tk.Widget):
    def __init__(self, fontsize=11, **kwargs):
        super().__init__(**kwargs)
        big_font(self, fontsize)


class SimpleLabel(Text, tk.Label):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class SimpleEntry(Text, tk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class SimpleCheckbutton(Text, tk.Checkbutton):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class SimpleRadiobutton(Text, tk.Radiobutton):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class SimpleText(Text, tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class SimpleTtkEntry(Text, tk.ttk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master=master, **kwargs)


class CanvasButton(Text, tk.Canvas):
    """Button emulation based on Canvas() widget. Can have text and/or preconfigured image."""
    def __init__(self, master=None, image=None, text=None, variable=None, width=None, height=None, textwidth=None,
                 textheight=None, fontsize=11, opacity=None, relief='raised', bg=None, bd=2, state='normal',
                 takefocus=True, command=None):
        super().__init__(master=master)
        self.pressed = False
        self.command = None
        bdsize = bd
        self.bg = bg
        # configure canvas itself with applicable options:
        standard_options = {}
        for item in ('width', 'height', 'relief', 'bg', 'bd', 'state', 'takefocus'):
            if eval(item) is not None:  # Such check because value of item can be 0.
                standard_options[item] = eval(item)
        super().config(**standard_options)
        self.bind("<Button-1>", self.press_button)
        self.bind("<ButtonRelease-1>", self.release_button)
        self.bind("<Configure>", self._place)       # Need to be before call of config_button()!
        # Configure widget with specific options:
        self.config_button(image=image, text=text, variable=variable, textwidth=textwidth, state=state,
                           textheight=textheight, fontsize=fontsize, opacity=opacity, bg=bg, command=command)
        # Get items dimensions:
        items_width = self.bbox('all')[2] - self.bbox('all')[0]
        items_height = self.bbox('all')[3] - self.bbox('all')[1]
        # Set widget size:
        if not width:
            self.config(width=items_width + items_width / 5 + bdsize * 2)
        if not height:
            self.config(height=items_height + ((items_height / 5) if image else (items_height / 2)) + bdsize * 2)
        # Place all contents in the middle of the widget:
        self.move('all', (self.winfo_reqwidth() - items_width) / 2,
                  (self.winfo_reqheight() - items_height) / 2)
        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        if callable(self.command):
            self.bind("<space>", lambda e: self.command())

    def __getitem__(self, item):
        if item == 'font':
            if hasattr(self, 'textlabel'):
                return self.textlabel['font']
        else:
            return super()[item]

    def bind(self, sequence=None, func=None, add=None):
        super().bind(sequence, func, add)
        for child in self.winfo_children():
            child.bind(sequence, func, add)

    def _place(self, event):
        """Correctly placing contents on widget resize."""
        y_move = (event.height - self.height) / 2
        x_move = (event.width - self.width) / 2
        self.move('all', x_move, y_move)
        self.height = event.height
        self.width = event.width

    def config_button(self, **kwargs):
        """Specific configuration of this widget."""
        if 'image' in kwargs and kwargs['image']:
            self.add_image(kwargs['image'], opacity='right' if 'opacity' not in kwargs else kwargs['opacity'])
        if 'text' in kwargs and kwargs['text']:
            text = kwargs['text']
        elif 'variable' in kwargs and kwargs['variable']:
            text = kwargs['variable']
        else:
            text = None
            # make textlabel look like other canvas parts:
            if hasattr(self, 'textlabel'):
                for option in ('bg', 'state', 'font'):
                    if option in kwargs and kwargs[option]:
                        self.textlabel.config(**{option: kwargs[option]})
        if text:
            self.add_text(text, **{key: kwargs[key] for key in ('fontsize', 'textwidth', 'textheight', 'bg', 'opacity')
                                   if key in kwargs})
        if 'command' in kwargs and kwargs['command']:
            self.command = kwargs['command']

    def config(self, **kwargs):
        default_options = {}
        for option in ('width', 'height', 'relief', 'bg', 'bd', 'state', 'takefocus'):
            if option in kwargs:
                default_options[option] = kwargs[option]
                if option not in ('bg', 'state', 'font'):
                    kwargs.pop(option)
        super().config(**default_options)
        self.config_button(**kwargs)

    def add_image(self, image, opacity='right'):
        """Add image."""
        coords = [0, 0]
        if self.bbox('image'):
            coords = self.coords('image')   # New image will appear in the same position as previous.
            self.delete('image')
        self.picture = tk.PhotoImage(file=image)    # 'self' need to override garbage collection action.
        self.create_image(coords[0], coords[1], image=self.picture, anchor='nw', tag='image')

    def add_text(self, textorvariable, fontsize=None, bg=None, opacity="right", textwidth=None, textheight=None):
        """Add text. Text can be tkinter.Variable() or string."""
        if fontsize:
            font = tk.font.Font(size=fontsize)
        else:
            font = tk.font.Font()
        if bg:
            self.bg = bg
        recreate = False
        if hasattr(self, 'textlabel'):
            coords = self.coords('text')    # New text will appear in the same position as previous.
            recreate = True
            self.delete(self.textlabel)
        if isinstance(textorvariable, tk.Variable):
            self.textlabel = tk.Label(self, textvariable=textorvariable, bd=0, bg=self.bg, font=font, justify='center',
                                      state=self.cget('state'), width=textwidth, height=textheight)
        else:
            self.textlabel = tk.Label(self, text=textorvariable, bd=0, bg=self.bg, font=font, justify='center',
                                      state=self.cget('state'), width=textwidth, height=textheight)
        if self.bbox('image'):
            x_multiplier = self.bbox('image')[2] - self.bbox('image')[0]
            x_divider = x_multiplier / 6
            y_multiplier = ((self.bbox('image')[3] - self.bbox('image')[1]) - self.textlabel.winfo_reqheight()) / 2
        else:
            x_multiplier = x_divider = y_multiplier = 0
        self.create_window(coords[0] if recreate else x_multiplier + x_divider, coords[1] if recreate else y_multiplier,
                           anchor='nw', window=self.textlabel, tags='text')
        # Swap text and image if needed:
        if opacity == 'left':
            self.move('text', -(x_divider + x_multiplier), 0)
            self.move('image', self.textlabel.winfo_reqwidth() + x_divider, 0)
        self.textlabel.bind("<Button-1>", self.press_button)
        self.textlabel.bind("<ButtonRelease-1>", self.release_button)

    def press_button(self, event):
        """Will be executed on button press."""
        if self.cget('state') == 'normal':
            self.config(relief='sunken')
            self.move('all', 1, 1)
            self.pressed = True

    def release_button(self, event):
        """Will be executed on mouse button release."""
        if self.cget('state') == 'normal' and self.pressed:
            self.config(relief='raised')
            self.move('all', -1, -1)
            if callable(self.command) and event.x_root in range(self.winfo_rootx(), self.winfo_rootx() +
                    self.winfo_width()) and event.y_root in range(self.winfo_rooty(), self.winfo_rooty() +
                    self.winfo_height()):
                self.command()
        self.pressed = False


class TaskButton(CanvasButton):
    """Just a button with some default parameters."""
    def __init__(self, parent, textwidth=8, **kwargs):
        super().__init__(master=parent, textwidth=textwidth, **kwargs)


class ScrolledCanvas(tk.Frame):
    """Scrollable Canvas. Scroll may be horizontal or vertical."""
    def __init__(self, parent=None, orientation="vertical", bd=2, **options):
        super().__init__(master=parent, relief='groove', bd=bd)
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
        self.canvbox.bind("<Configure>", self.reconf_canvas)
        self.canvbox.pack(fill="x" if orientation == "horizontal" else "both", expand=1)

    def reconf_canvas(self, event):
        """Resizing of canvas scrollable region."""
        self.canvbox.configure(scrollregion=self.canvbox.bbox('all'))
        self.canvbox.config(height=self.content_frame.winfo_height())


def big_font(unit, size=9):
    """Font size of a given unit change."""
    fontname = tk.font.Font(font=unit['font']).actual()['family']
    unit.config(font=(fontname, size))