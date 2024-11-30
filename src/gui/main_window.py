import asyncio
import threading
import tkinter as tk
from tkinter import ttk

from src.gui.error_window import ErrorWindow
from src.gui.initialization_window import InitializationWindow
from src.gui.state_manager import global_state_manager


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.init_window = InitializationWindow(root)

        self.app_logic = None
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_event_loop, daemon=True).start()

        self.root.title("Ontology Enrichment Application")
        self.root.geometry("1000x600")
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f5f5f5")
        self.style.configure("MainButton.TButton", font=("Arial", 13), padding=5, background="#D3D3D3",
                             foreground="#000080")
        self.style.configure("TLabel", font=("Arial", 11), background="#f5f5f5")
        self.style.configure("TNotebook", background="#f5f5f5", tabposition="nw")
        self.style.configure("TNotebook")
        self.style.configure("TNotebook.Tab", padding=[5, 5], font=("Arial", 11), relief="ridge")

        self.notebook = ttk.Notebook(root, style="TNotebook")
        for tab_name, callback_name in {"Added individuals": "update_added_individuals_tab",
                                        " ChatGPT request ": "update_ChatGPT_request_tab",
                                        "ChatGPT response": "update_ChatGPT_response_tab",
                                        "         Errors         ": "update_errors_tab"}.items():
            tab = tk.Frame(self.notebook)
            self.notebook.add(tab, text=tab_name)
            text_area = tk.Text(tab, bg='#7F84FA', padx=5, pady=5)
            scrollbar = tk.Scrollbar(tab, orient='vertical', command=text_area.yview)
            scrollbar.pack(side='right', fill='y')
            text_area.pack(expand=True, fill='both')
            text_area.config(yscrollcommand=scrollbar.set)
            global_state_manager.register_callback(callback_name, self.create_callback(text_area))

        self.notebook.pack(side="right", expand=True, fill="both")

        left_frame = ttk.Frame(root, width=200, height=100, style="TFrame")
        left_frame.pack(side="left", fill="y")
        left_frame.pack_propagate(False)

        self.url_count = tk.IntVar(value=0)
        self.individuals_count = tk.IntVar(value=0)
        self.obj_props_count = tk.IntVar(value=0)
        self.data_props_count = tk.IntVar(value=0)

        global_state_manager.register_callback("update_url_count", lambda value: self.url_count.set(self.url_count.get()+value))
        global_state_manager.register_callback("update_individuals_count", lambda value: self.individuals_count.set(self.url_count.get()+value))
        global_state_manager.register_callback("update_obj_props_count", lambda value: self.obj_props_count.set(self.obj_props_count.get()+value))
        global_state_manager.register_callback("update_data_props_count", lambda value: self.data_props_count.set(self.data_props_count.get()+value))
        global_state_manager.register_callback("switch_button_to_start", lambda value: self.start_stop_button.config(text="Start", command=self.start_processing))
        counters = [
            ("URLs", self.url_count),
            ("Individuals", self.individuals_count),
            ("Obj Props", self.obj_props_count),
            ("Data Props", self.data_props_count)
        ]
        for label_text, counter in counters:
            frame = ttk.Frame(left_frame, style="TFrame")
            frame.pack(fill="x", padx=10, pady=5)
            ttk.Label(frame, text=label_text, style="TLabel").pack(side="left")
            ttk.Label(frame, textvariable=counter, style="TLabel").pack(side="right")

        button_frame = ttk.Frame(left_frame, style="TFrame")
        button_frame.pack(side="bottom", pady=20)

        ttk.Button(button_frame, text="Initialize", command=self.show_initialize_window,
                   style="MainButton.TButton").pack(side="top", pady=5)

        self.start_stop_button = ttk.Button(button_frame, text="Start", command=self.start_processing, style="MainButton.TButton")
        self.start_stop_button.pack(side="top", pady=5)



    def show_initialize_window(self):
        if not self.init_window.is_exist():
            self.init_window = InitializationWindow(self.root)
        self.init_window.show()


    def start_processing(self):
        global_state_manager.set_state('processing', True)
        self.app_logic = self.init_window.get_logic_object()
        if self.app_logic is None:
            ErrorWindow(self.root, "The application was not initialized.")
            return
        self.loop.call_soon_threadsafe(asyncio.create_task, self.app_logic.run(5))
        self.start_stop_button.config(text="Stop", command=self.stop_processing)

    def stop_processing(self):
        global_state_manager.set_state('processing', False)
        self.start_stop_button.config(text="Start", command=self.start_processing)

    def start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def create_callback(self, text_area):
        return lambda value: text_area.insert("end", f"{value}\n\n")



