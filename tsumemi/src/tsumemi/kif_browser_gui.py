from __future__ import annotations

import configparser
import functools
import os
import tkinter as tk

from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

import tsumemi.src.tsumemi.event as evt
import tsumemi.src.tsumemi.model as model
import tsumemi.src.tsumemi.problem_list as plist
import tsumemi.src.tsumemi.problem_list_controller as plistcon
import tsumemi.src.tsumemi.timer as timer
import tsumemi.src.tsumemi.timer_controller as timecon

from tsumemi.src.tsumemi.board_canvas import BoardCanvas
from tsumemi.src.tsumemi.move_input_handler import MoveInputHandler
from tsumemi.src.tsumemi.nav_controls import FreeModeNavControls, SpeedrunNavControls
from tsumemi.src.tsumemi.settings_window import SettingsWindow, CONFIG_PATH

if TYPE_CHECKING:
    from typing import Any, Callable, Optional


class Menubar(tk.Menu):
    """GUI class for the menubar at the top of the main window.
    """
    def __init__(self, parent, controller, *args, **kwargs):
        self.controller = controller
        super().__init__(parent, *args, **kwargs)
        
        # Set cascades
        menu_file = tk.Menu(self)
        self.add_cascade(menu=menu_file, label="File")
        menu_settings = tk.Menu(self)
        self.add_cascade(menu=menu_settings, label="Settings")
        menu_help = tk.Menu(self)
        self.add_cascade(menu=menu_help, label="Help")
        
        # File
        menu_file.add_command(
            label="Open folder...",
            command=self.controller.open_folder,
            accelerator="Ctrl+O",
            underline=0
        )
        menu_file.add_command(
            label="Open all subfolders...",
            command=self.controller.open_folder_recursive,
            accelerator="Ctrl+Shift+O",
        )
        # Settings
        menu_settings.add_command(
            label="Settings...",
            command=lambda: SettingsWindow(controller=self.controller)
        )
        # Help
        menu_help.add_command(
            label="About kif-browser",
            command=functools.partial(
                messagebox.showinfo,
                title="About kif-browser",
                message="Written in Python 3 for the shogi community. KIF files sold separately."
            )
        )
        # Bind to main window
        parent["menu"] = self
        return

'''
class ProblemsView(ttk.Treeview, evt.IObserver):
    """GUI class to display list of problems.
    Uses the Observer pattern to update itself whenever underlying
    problem list updates.
    """
    def __init__(self, parent, controller, problem_list, *args, **kwargs):
        self.controller = controller
        super().__init__(parent, *args, **kwargs)
        self.problem_list = problem_list
        # Register self as observer of ProblemList
        self.problem_list.add_observer(self)
        
        self.NOTIFY_ACTIONS = {
            plist.ProbStatusEvent: self.display_status,
            plist.ProbTimeEvent: self.display_time,
            plist.ProbListEvent: self.refresh_view
        }
        self.status_strings = {
            plist.ProblemStatus.NONE: "",
            plist.ProblemStatus.SKIP: "-",
            plist.ProblemStatus.CORRECT: "O",
            plist.ProblemStatus.WRONG: "X"
        }
        
        self["columns"] = ("filename", "time", "status")
        self["show"] = "headings"
        self.heading("filename", text="Problem", command=self.problem_list.sort_by_file)
        self.heading("time", text="Time", command=self.problem_list.sort_by_time)
        self.column("time", width=120)
        self.heading("status", text="Status", command=self.problem_list.sort_by_status)
        self.column("status", anchor="center", width=40)
        # Colours to be decided (accessibility concerns)
        self.tag_configure("SKIP", background="snow2")
        self.tag_configure("CORRECT", background="PaleGreen1")
        self.tag_configure("WRONG", background="LightPink1")
        
        # Bind double click to go to problem
        self.bind("<Double-1>",
            lambda e: self.controller.model.go_to_file(
                idx=self.get_idx_on_click(e)
            )
        )
        return
    
    def display_time(self, event):
        idx = event.idx
        time = event.time
        # Set time column for item at given index
        id = self.get_children()[idx]
        time_str = timer.sec_to_str(time)
        self.set(id, column="time", value=time_str)
        return
    
    def display_status(self, event):
        idx = event.idx
        status = event.status
        id = self.get_children()[idx]
        self.set(id, column="status", value=self.status_strings[status])
        self.item(id, tags=[status.name]) # overrides existing tags
        return
    
    def refresh_view(self, event):
        # Refresh the entire view as the model changed, e.g. on opening folder
        problems = event.prob_list
        self.delete(*self.get_children())
        for problem in problems:
            filename = os.path.basename(problem.filepath)
            time_str = ("-" if problem.time is None
                        else timer.sec_to_str(problem.time))
            status_str = self.status_strings[problem.status]
            self.insert(
                "", "end",
                values=(filename, time_str, status_str),
                tags=[problem.status.name]
            )
        return
    
    def get_idx_on_click(self, event):
        if self.identify_region(event.x, event.y) == "cell":
            return self.index(self.identify_row(event.y))
        else:
            return None


class ProblemListPane(ttk.Frame):
    """GUI frame containing view of problem list and associated
    controls.
    """
    def __init__(self, parent, controller, problem_list, *args, **kwargs):
        self.controller = controller
        super().__init__(parent, *args, **kwargs)
        self.problem_list = problem_list
        
        # Display problem list as Treeview
        self.tvw = ProblemsView(
            parent=self, controller=controller, problem_list=problem_list
        )
        self.tvw.grid(column=0, row=0, sticky="NSEW")
        
        # Make scrollbar
        self.scrollbar_tvw = ttk.Scrollbar(
            self, orient="vertical",
            command=self.tvw.yview
        )
        self.scrollbar_tvw.grid(column=1, row=0, sticky="NS")
        self.tvw["yscrollcommand"] = self.scrollbar_tvw.set
        
        # Make randomise button
        self.btn_randomise = ttk.Button(
            self, text="Randomise problems",
            command=self.problem_list.randomise
        )
        self.btn_randomise.grid(column=0, row=1)
        
        # Make speedrun mode button
        self.btn_speedrun = ttk.Button(
            self, text="Start speedrun",
            command=controller.model.start_speedrun
        )
        self.btn_speedrun.grid(column=0, row=2)
        self.btn_speedrun.grid_remove()
        self.btn_abort_speedrun = ttk.Button(
            self, text="Abort speedrun",
            command=controller.model.abort_speedrun
        )
        self.btn_abort_speedrun.grid(column=0, row=2)
        self.btn_abort_speedrun.grid_remove()
        
        self.btn_speedrun.grid()
'''

class RootController:
    """Root controller for the application. Manages top-level logic
    and GUI elements.
    """
    # eventually, refactor menu labels and dialog out into a constant namespace
    def __init__(self, root: tk.Tk) -> None:
        # tkinter stuff, set up the main window
        self.root: tk.Tk = root
        self.root.option_add("*tearOff", False)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.title("KIF folder browser")
        
        # Create settings file if none exists
        self.config = configparser.ConfigParser(dict_type=dict)
        try:
            with open(CONFIG_PATH, "r") as configfile:
                self.config.read_file(configfile)
        except FileNotFoundError:
            with open(CONFIG_PATH, "w+") as configfile:
                # write a default config.ini
                configfile.write("[skins]\n")
                configfile.write("pieces = TEXT\n")
                configfile.write("board = BROWN\n")
                configfile.write("komadai = WHITE\n")
            with open(CONFIG_PATH, "r") as configfile:
                self.config.read_file(configfile)
        
        # mainframe is the main frame of the root window
        self.mainframe = ttk.Frame(self.root)
        self.mainframe.grid(column=0, row=0, sticky="NSEW")
        self.mainframe.columnconfigure(0, weight=1)
        self.mainframe.columnconfigure(1, weight=1)
        self.mainframe.rowconfigure(0, weight=1)
        
        # Make menubar
        self.menubar = Menubar(parent=self.root, controller=self)
        
        # Set up data model
        self.model = model.Model(gui_controller=self)
        
        # Make canvas for board
        self.boardWrapper = ttk.Frame(self.mainframe)
        self.boardWrapper.grid(column=0, row=0, sticky="NSEW")
        self.boardWrapper.columnconfigure(0, weight=1)
        self.boardWrapper.rowconfigure(0, weight=1)
        self.boardWrapper.grid_configure(padx=5, pady=5)
        
        self.board = BoardCanvas(
            parent=self.boardWrapper, controller=self,
            game = self.model.active_game,
            width=BoardCanvas.CANVAS_WIDTH, height=BoardCanvas.CANVAS_HEIGHT,
            bg="white"
        )
        self.board.grid(column=0, row=0, sticky="NSEW")
        self.board.bind("<Configure>", self.board.on_resize)
        self.move_input_handler = MoveInputHandler(self.board)
        self.move_input_handler.add_observer(self.model)
        
        # Initialise solution text
        self.is_solution_shown = False
        self.solution = tk.StringVar(value="Open a folder of problems to display.")
        self.lbl_solution = ttk.Label(
            self.mainframe, textvariable=self.solution,
            justify="left", wraplength=self.board.CANVAS_WIDTH
        )
        self.lbl_solution.grid(
            column=0, row=1, sticky="W"
        )
        self.lbl_solution.grid_configure(padx=5, pady=5)
        
        # Initialise nav controls and select one to begin with
        self._navcons = {
            "free" : FreeModeNavControls(
                parent=self.mainframe, controller=self
            ),
            "speedrun" : SpeedrunNavControls(
                parent=self.mainframe, controller=self
            )
        }
        for navcon in self._navcons.values():
            navcon.grid(column=0, row=2)
            navcon.grid_remove()
        self.nav_controls = self._navcons["free"]
        self.nav_controls.grid()
        
        # Timer controls and display
        self.main_timer = timecon.TimerController(parent=self.mainframe)
        self.main_timer.clock.add_observer(self.model)
        self.timer_controls = self.main_timer.view
        self.timer_controls.grid(column=1, row=1)
        self.timer_controls.columnconfigure(0, weight=0)
        self.timer_controls.rowconfigure(0, weight=0)
        
        # Problem list
        self.main_problem_list = plistcon.ProblemListController(
            parent=self.mainframe, controller=self
        )
        self.model.main_prob_buffer = self.main_problem_list.problem_list
        self.problem_list_pane = self.main_problem_list.view
        # self.problem_list_pane = ProblemListPane(
            # parent=self.mainframe, controller=self,
            # problem_list=self.model.main_prob_buffer
        # )
        self.problem_list_pane.grid(column=1, row=0, sticky="NSEW")
        self.problem_list_pane.columnconfigure(0, weight=1)
        self.problem_list_pane.rowconfigure(0, weight=1)
        self.problem_list_pane.grid_configure(padx=5, pady=5)
        
        # Keyboard shortcuts
        self.bindings = Bindings(self)
        self.bindings.bind_shortcuts(self.root, self.bindings.MASTER_SHORTCUTS)
        self.bindings.bind_shortcuts(self.root, self.bindings.FREE_SHORTCUTS)
        return
    
    #=== GUI display methods
    def display_problem(self) -> None:
        self.board.draw()
        self.hide_solution()
        self.root.title(
            "KIF folder browser - "
            + str(self.model.get_curr_filepath())
        )
        return
    
    def hide_solution(self) -> None:
        self.solution.set("[solution hidden]")
        self.is_solution_shown = False
        return
    
    def show_solution(self) -> None:
        self.solution.set(self.model.solution)
        self.is_solution_shown = True
        return
    
    def toggle_solution(self, event: Optional[tk.Event] = None) -> None:
        if self.is_solution_shown:
            self.hide_solution()
        else:
            self.show_solution()
        return
    
    def flip_board(self, want_upside_down: bool) -> None:
        self.board.flip_board(want_upside_down)
        return
    
    #=== Open folder, needs file open dialog
    def open_folder(self, event: Optional[tk.Event] = None,
            recursive: bool = False
        ) -> None:
        directory = filedialog.askdirectory()
        if directory == "":
            return
        directory = os.path.normpath(directory)
        if self.model.set_directory(directory, recursive=recursive):
            # Iff any KIF files were found, read the first and show it
            self.display_problem()
        return
    
    def open_folder_recursive(self, event: Optional[tk.Event] = None) -> None:
        return self.open_folder(event, recursive=True)
    
    # Speedrun mode commands
    def split_timer(self) -> None:
        time = self.main_timer.clock.split()
        if time is not None:
            self.model.main_prob_buffer.set_time(time)
        return
    
    def set_speedrun_ui(self) -> None:
        # Make UI changes
        self.nav_controls.grid_remove()
        self.nav_controls = self._navcons["speedrun"]
        self.nav_controls.show_sol_skip()
        self.nav_controls.grid()
        self.problem_list_pane.btn_speedrun.grid_remove()
        self.problem_list_pane.btn_abort_speedrun.grid()
        # Set application state
        self.bindings.unbind_shortcuts(self.root, self.bindings.FREE_SHORTCUTS)
        return
    
    def remove_speedrun_ui(self) -> None:
        # Abort speedrun, go back to free browsing
        # Make UI changes
        self.nav_controls.grid_remove()
        self.nav_controls = self._navcons["free"]
        self.nav_controls.grid()
        self.problem_list_pane.btn_speedrun.grid()
        self.problem_list_pane.btn_abort_speedrun.grid_remove()
        # Set application state
        self.bindings.bind_shortcuts(self.root, self.bindings.FREE_SHORTCUTS)
        return
    
    def view_solution(self) -> None:
        self.split_timer()
        self.main_timer.clock.stop()
        self.show_solution()
        self.nav_controls.show_correct_wrong()
        return
    
    def show_end_of_folder_message(self) -> None:
        messagebox.showinfo(
            title="End of folder",
            message="You have reached the end of the speedrun."
        )
        return


class Bindings:
    # Just to group all shortcut bindings together for convenience.
    def __init__(self, controller):
        self.controller = controller
    
        self.MASTER_SHORTCUTS = {
            "<Control-o>": self.controller.open_folder,
            "<Control-O>": self.controller.open_folder,
            "<Control-Shift-O>": self.controller.open_folder_recursive,
            "<Control-Shift-o>": self.controller.open_folder_recursive
        }
        
        self.FREE_SHORTCUTS = {
            "<Key-h>": self.controller.toggle_solution,
            "<Key-H>": self.controller.toggle_solution,
            "<Left>": self.controller.model.go_to_prev_file,
            "<Right>": self.controller.model.go_to_next_file
        }
        
        self.SPEEDRUN_SHORTCUTS = {}
    
    @staticmethod
    def bind_shortcuts(target, shortcuts):
        for keypress, command in shortcuts.items():
            target.bind(keypress, command)
        return
    
    @staticmethod
    def unbind_shortcuts(target, shortcuts):
        for keypress in shortcuts.keys():
            target.unbind(keypress)
        return


def run():
    def apply_theme_fix():
        # Fix from pyIDM on GitHub:
        # https://github.com/pyIDM/PyIDM/issues/128#issuecomment-655477524
        # fix for table colors in tkinter 8.6.9,
        # call style.map twice to work properly
        style = ttk.Style()
        def fixed_map(option):
            return [elm for elm in style.map('Treeview', query_opt=option)
                    if elm[:2] != ("!disabled", "!selected")]
        style.map('Treeview', foreground=fixed_map("foreground"),
                  background=fixed_map("background"))
        style.map('Treeview', foreground=fixed_map("foreground"),
                  background=fixed_map("background"))

    root = tk.Tk()
    root_controller = RootController(root)
    apply_theme_fix()
    root.minsize(width=400, height=200) # stopgap vs canvas overshrinking bug
    root.mainloop()