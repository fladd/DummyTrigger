"""DummyTrigger

A small application to send triggers (custom extended ASCII character) to a
serial port in regular intervals, emulating the trigger from an MR scanner.

"""


__author__ = "Florian Krause <me@floriankrause.org>"
__version__ = "0.2.0"


import time
import platform
import sys
if sys.version[0] == '3':
    PYTHON3 = True
    import tkinter as tk
    import tkinter.ttk as ttk
    from tkinter import scrolledtext
    from tkinter import filedialog
    from tkinter import messagebox
    from tkinter import font as tkFont
else:
    PYTHON3 = False
    import Tkinter as tk
    import ttk as ttk
    import ScrolledText as scrolledtext
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import tkFont

import serial
from serial.tools.list_ports import comports


try:
    time = time.perf_counter
except:
    time = time.time


class Spinbox(ttk.Entry):
    def __init__(self, master=None, **kw):
        s = ttk.Style()
        ttk.Entry.__init__(self, master, "ttk::spinbox", **kw)

    def current(self, newindex=None):
        return self.tk.call(self._w, 'current', newindex)

    def set(self, value):
        return self.tk.call(self._w, 'set', value)


class MainApplication(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.running = True
        self.started = False
        self.create_widgets()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.menubar = tk.Menu(parent)
        if platform.system() == "Darwin":
            self.apple_menu = tk.Menu(self.menubar, name="apple")
            self.menubar.add_cascade(menu=self.apple_menu)
            self.apple_menu.add_command(
                label="About DummyTrigger",
                command=lambda: AboutDialogue(self.parent).show())
        else:
            self.help_menu = tk.Menu(self.menubar)
            self.menubar.add_cascade(menu=self.help_menu, label="Help")
            self.help_menu.add_command(
                label="About DummyTrigger",
                command=lambda: AboutDialogue(self.parent).show())
        self.parent["menu"] = self.menubar

    def create_widgets(self):
        """Contains all widgets in main application."""

        tr_vcmd = (self.register(self.validate_tr), '%P', '%s', '%S')
        volumes_vcmd = (self.register(self.validate_volumes), '%P', '%s', '%S')
        code_vcmd = (self.register(self.validate_code), '%P', '%s', '%S')

        settings_frame = ttk.Labelframe(self, text='Settings',
                                        padding="5 5 5 5")
        settings_frame.columnconfigure(2, weight=1)
        settings_frame.grid(column=0, row=0, sticky="nesw")
        ports = sorted([x.device for x in comports()])
        port_label = ttk.Label(settings_frame, text="Port:")
        port_label.grid(column=0, row=0, sticky="nes")
        self.port_menu = ttk.Combobox(settings_frame)
        self.port_menu['state'] = "readonly"
        self.port_menu['values'] = ports
        try:
            self.port_menu.set(ports[0])
        except:
            pass
        self.port_menu.grid(column=1, row=0, columnspan=2, sticky="nesw")
        baudrate_label = ttk.Label(settings_frame, text="Baudrate:")
        baudrate_label.grid(column=0, row=1, sticky="nes")
        self.baudrate_menu = ttk.Combobox(settings_frame)
        self.baudrate_menu['state'] = "readonly"
        self.baudrate_menu['values'] = ["50", "75", "110", "134", "150", "200",
                                        "300", "600", "1200", "1800", "2400",
                                        "4800", "9600", "19200", "38400",
                                        "57600", "115200"]
        self.baudrate_menu.set("115200")
        self.baudrate_menu.grid(column=1, row=1, columnspan=2, sticky="news")
        tr_label = ttk.Label(settings_frame, text="TR:")
        tr_label.grid(column=0, row=2, sticky="nes")
        self.tr = tk.StringVar()
        self.tr.set("2000")
        self.tr.trace('w', lambda nm, idx, mode,
                      var=self.tr: self.update_time())
        self.tr_entry = Spinbox(settings_frame, from_=100, to=9999,
                                textvariable=self.tr, width=4, validate='all',
                                validatecommand=tr_vcmd)
        self.tr_entry.grid(column=1, row=2, sticky="nesw")
        ttk.Label(settings_frame, text="ms").grid(column=2, row=2, sticky="nsw")
        volumes_label = ttk.Label(settings_frame, text="Measurements:")
        volumes_label.grid(column=0, row=3, sticky="nes")
        self.volumes = tk.StringVar()
        self.volumes.set("100")
        self.volumes.trace('w', lambda nm, idx, mode,
                           var=self.volumes: self.update_time())
        self.volumes_entry = Spinbox(settings_frame, from_=1, to=9999,
                                     textvariable=self.volumes, width=4,
                                     validate='all',
                                     validatecommand=volumes_vcmd)
        self.volumes_entry.grid(column=1, row=3, sticky="nesw")
        code_label = ttk.Label(settings_frame, text="Code:")
        code_label.grid(column=0, row=4, sticky="nes")
        self.code = tk.StringVar()
        self.code.set("33")
        self.code_entry = Spinbox(settings_frame, from_=0, to=255,
                                  textvariable=self.code, width=3,
                                  validate='all',
                                  validatecommand=code_vcmd)
        self.code_entry.grid(column=1, row=4, sticky="news")
        self.character = tk.StringVar()
        self.update_character()
        self.character_label = ttk.Label(settings_frame,
                                         textvariable=self.character)
        self.character_label.grid(column=2, row=4, sticky="nsw")

        self.code.trace('w', self.update_character)

        bottom_frame = ttk.Frame(self)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.grid(column=0, row=1, sticky="nesw")
        self.time = tk.StringVar()
        self.update_time()
        self.time_label = ttk.Label(bottom_frame, textvariable=self.time)
        self.time_label.grid(column=0, row=0, sticky="nsw")
        ttk.Style().configure("Green.TButton", background='green')
        ttk.Style().map("Green.TButton", background=[('active', 'green')])
        ttk.Style().configure("Orange.TButton", background='orange')
        ttk.Style().map("Orange.TButton", background=[('active', 'orange')])
        ttk.Style().configure("Red.TButton", background='red')
        ttk.Style().map("Red.TButton", background=[('active', 'red')])
        self.button = ttk.Button(bottom_frame, text="Start",
                                 command=self.start_stop)
        self.button.configure(style="Green.TButton")
        self.button.grid(column=1, row=0, sticky="nes")

        for child in settings_frame.winfo_children():
            child.grid_configure(padx=5, pady=5)
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def validate_tr(self, P, s, S):
        valid = (S.isdigit() and len(P) <= 4)
        if valid:
            self.update_time()
            if len(P) < 2:
                self.button['state'] = "disabled"
            else:
                self.button['state'] = "normal"
        else:
            self.tr.set(s)
        return valid

    def validate_volumes(self, P, s, S):
        valid = (S.isdigit() and len(P) <= 4)
        if valid:
            self.update_time()
            if len(P) < 1:
                self.button['state'] = "disabled"
            else:
                self.button['state'] = "normal"
        else:
            self.volumes.set(s)
        return valid

    def validate_code(self, P, s, S):
        if len(P) == 0:
            valid = S.isdigit()
        else:
            valid = S.isdigit() and 0 <= int(P) <= 255
        if valid:
            if len(P) < 1:
                self.button['state'] = "disabled"
            else:
                self.button['state'] = "normal"
        else:
            self.code.set(s)
        return valid

    def update_character(self, *args):
        code = self.code.get()
        if code != "" and int(code) >= 32:
            self.character.set(chr(int(code)))

    def start_stop(self):
        if not self.started:
            try:
                port = self.port_menu.get()
                baudrate = self.baudrate_menu.get()
                self.serial = serial.Serial(port, baudrate=baudrate,
                                            write_timeout=0)
                self.port_menu['state'] = "disabled"
                self.tr_entry['state'] = "disabled"
                self.volumes_entry['state'] = "disabled"
                self.button.configure(style="Orange.TButton")
                countdown_start = time()
                while True:
                    elapsed = time() - countdown_start
                    if round((elapsed * 1000) % 1000) == 0:
                        self.button.configure(text="{0}".format(
                            5 - int(elapsed)))
                    if (time() - countdown_start) * 1000 >= 5000:
                        break
                    root.update()
                self.button.configure(style="Red.TButton")
                self.button.configure(text="Stop")
                self.start_time = time()
                self.last_update = self.start_time
                self.started = True
                self.first_trigger = True
                self.update_time()
                self.trigger()
            except:
                pass
        else:
            try:
                self.serial.close()
            except:
                pass
            self.port_menu['state'] = "readonly"
            self.tr_entry['state'] = "normal"
            self.volumes_entry['state'] = "normal"
            self.button.configure(style="Green.TButton")
            self.button.configure(text="Start")
            self.started = False
            self.update_time()

    def trigger(self):
        code = int(self.code.get())
        if self.first_trigger:
            if PYTHON3:
                self.serial.write(bytes([code]))
            else:
                self.serial.write(chr(code))
            self.first_trigger = False
        tr = int(self.tr.get())
        if tr * int(self.volumes.get()) - 11 <= int((time() - \
                                                     self.start_time) * 1000):
            self.start_stop()
        elif int((time() - self.last_update) * 1000) >= tr - 10:
            while int((time() - self.last_update) * 1000) < tr:
                pass
            self.last_update = time()
            if PYTHON3:
                self.serial.write(bytes([code]))
            else:
                self.serial.write(chr(code))
            self.update_time()
        elif int((time() - self.last_update) * 1000) == 1000:
            self.update_time()

    def update_time(self):
        try:
            tr = int(self.tr.get())
            vols = int(self.volumes.get())
            total = tr * vols
            current = 0
            if self.started:
                current = int(((time() - self.start_time) * 1000) / tr) + 1
                total = total - int((time() - self.start_time) * 1000)
            s = int(round((total / 1000) % 60))
            m = int(round((total / (1000 * 60)) % 60))
            self.time.set("Scanning: {0:02d}:{1:02d} ({2}/{3})".format(
                m, s, current, vols))
            root.update()
        except:
            self.time.set("Scanning: --:--")

    def quit(self):
        self.running = False

    def about(self):
        pass


class AboutDialogue:
    def __init__(self, parent):
        self.parent = parent
        top = self.top = tk.Toplevel(parent, background="grey85")
        top.title("About {0}".format(__doc__.split('\n', 1)[0]))
        frame = ttk.Frame(top)
        frame.pack(padx=10, pady=10)

        name = ttk.Label(frame, text=__doc__.split('\n', 1)[0])
        f = tkFont.Font(font=name['font'])
        f['weight'] = 'bold'
        name['font'] = f.name
        name.pack(pady=5)
        version = ttk.Label(frame, text=__version__)
        version.pack(pady=5)
        author = ttk.Label(frame, text=__author__)
        f = tkFont.Font(font=name['font'])
        f['size'] = '10'
        f['weight'] = 'normal'
        f['slant'] = 'italic'
        author['font'] = f.name
        author.pack(pady=5)
        empty = ttk.Label(frame, text="")
        empty.pack(pady=5)
        b = ttk.Button(frame, text="OK", command=self.ok)
        b.pack(pady=5)

    def ok(self):
        self.top.destroy()

    def show(self):
        self.parent.wait_window(self.top)


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("default")
    root.title(__doc__.split("\n")[0])
    root.resizable(False, False)
    root.option_add('*tearOff', tk.FALSE)
    app = MainApplication(root, padding="5 5 5 5")
    app.pack(side="top", fill="both", expand=True)
    root.protocol("WM_DELETE_WINDOW", app.quit)
    while app.running:
        if app.started:
            app.trigger()
        root.update()
