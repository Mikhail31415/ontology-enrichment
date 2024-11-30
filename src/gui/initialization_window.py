import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import aiofiles
import yaml
from owlready2 import get_ontology

from src.application_logic import AppLogic
from src.exception.input_exception import InputError
from src.gui.error_window import ErrorWindow
from src.prompt_generator import generate_prompt


async def place_generator_from_file(file_path):
    async with aiofiles.open(file_path, 'r') as f:
        async for line in f:
            yield line


async def single_place_generator(place):
    yield place


def load_config(path):
    with open(path, 'r') as f:
        configs = yaml.safe_load(f)
        return configs


def prompt_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_onto(path):
    try:
        return get_ontology(path).load()
    except Exception:
        raise InputError("Failed to load ontology. Please check the path and try again.")


class InitializationWindow:
    def __init__(self, root):
        self.root = root
        self.app_logic = None
        self.init_win = tk.Toplevel(root)
        self.init_win.title("Initialize Configuration")
        self.init_win.geometry("500x560")
        self.init_win.withdraw()
        self.style = ttk.Style()
        self.style.configure("TLabelframe", background="#f5f5f5", padding=10)

        ttk.Label(self.init_win, text="Select Source Type:").pack(anchor="w", padx=10, pady=5)
        self.source_type = tk.StringVar(value="Single URL")
        options = [("Single URL", "Single URL"), ("URLs file", "URLs file"), ("NL text file", "NL text file"),
                   ("NL paths file", "NL paths file")]
        for text, mode in options:
            ttk.Radiobutton(self.init_win, text=text, variable=self.source_type, value=mode).pack(anchor="w", padx=20)

        self.place_source_entry = ttk.Entry(self.init_win)
        self.place_source_entry.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.init_win, text="Ontology Path:").pack(anchor="w", padx=10, pady=5)
        self.ontology_path_entry = ttk.Entry(self.init_win)
        self.ontology_path_entry.pack(fill="x", padx=10)

        ttk.Label(self.init_win, text="Save Ontology Path:").pack(anchor="w", padx=10, pady=5)
        self.save_ontology_path_entry = ttk.Entry(self.init_win)
        self.save_ontology_path_entry.pack(fill="x", padx=10)

        ttk.Label(self.init_win, text="Prompt Configuration:").pack(anchor="w", padx=10, pady=5)
        self.prompt_source = tk.StringVar(value="Prompt")

        radio_frame = ttk.Frame(self.init_win)
        radio_frame.pack(anchor="w", padx=20, pady=5)
        ttk.Radiobutton(radio_frame, text="Prompt", variable=self.prompt_source, value="Prompt").pack(side="left")
        ttk.Radiobutton(radio_frame, text="Path to file with prompt", variable=self.prompt_source, value="File").pack(
            side="left")
        ttk.Button(radio_frame, text="Generate", command=self.generate_prompt).pack(side="left", padx=10)

        frame = tk.Frame(self.init_win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.prompt_entry = tk.Text(frame, height=10, wrap="word", padx=5, pady=5)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.prompt_entry.yview)
        scrollbar.pack(side="right", fill="y")
        self.prompt_entry.pack(side="left", fill="both", expand=True)
        self.prompt_entry.config(yscrollcommand=scrollbar.set)

        self.confirm_button = ttk.Button(self.init_win, text="Confirm", command=self.initialize_app_logic,
                                         style="MainButton.TButton")
        self.confirm_button.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self.init_win, mode='indeterminate')

    def show(self):
        self.init_win.deiconify()

    def hide(self):
        self.init_win.withdraw()

    def generate_prompt(self):
        try:
            onto = load_onto(self.ontology_path_entry.get())
            self.prompt_entry.insert("1.0", generate_prompt(onto))
        except InputError as e:
            ErrorWindow(self.root, e.message)
            return

    def initialize_app_logic(self):
        self.confirm_button.state(['disabled'])
        try:
            onto = load_onto(self.ontology_path_entry.get())
            save_ontology_path = self.save_ontology_path_entry.get()

            InputValidator.validate_save_path(save_ontology_path)

            if self.prompt_source.get() == 'File':
                InputValidator.validate_read_path(self.prompt_entry.get("1.0", "end-1c"))
                prompt = prompt_from_file(self.prompt_entry.get("1.0", "end-1c"))
            else:
                prompt = self.prompt_entry.get("1.0", "end-1c")

            if self.source_type.get() == 'Single URL' or self.source_type.get() == 'URLs file':
                mode = 'url'
            if self.source_type.get() == 'NL text file' or self.source_type.get() == 'NL paths file':
                mode = 'nl_file'


            place_entry = self.place_source_entry.get()
            if self.source_type.get() == 'URLs file' or self.source_type.get() == 'NL paths file' or self.source_type.get() == 'NL text file':
                InputValidator.validate_read_path(place_entry)
            if self.source_type.get() == 'Single URL' or self.source_type.get() == 'NL text file':
                generator = single_place_generator(place_entry)
            if self.source_type.get() == 'URLs file' or self.source_type.get() == 'NL paths file':
                generator = place_generator_from_file(place_entry)

        except InputError as e:
            ErrorWindow(self.init_win, e.message)
            self.confirm_button.state(['!disabled'])
            return
        try:
            self.app_logic = AppLogic(place_generator=generator, prompt=prompt,
                                      onto=onto,
                                      save_ontology_path=save_ontology_path,
                                      mode=mode)
        except Exception as e:
            ErrorWindow(self.init_win, "Wrong configs: \n" + str(e))
            self.confirm_button.state(['!disabled'])
            return

        self.init_win.withdraw()
        self.confirm_button.state(['!disabled'])

    def get_logic_object(self):
        return self.app_logic

    def is_exist(self):
        return self.init_win.winfo_exists()

class InputValidator:
    @staticmethod
    def validate_save_path(save_path):
        directory = Path(save_path).parent
        if not directory.exists():
            raise InputError("The specified directory for saving the ontology does not exist.")
        if not os.access(directory, os.W_OK):
            raise InputError("No write permission for the specified directory.")

    @staticmethod
    def validate_read_path(read_path):
        path = Path(read_path)
        if not path.is_file():
            raise InputError("The specified file path does not exist or is not a file.")
        if not os.access(path, os.R_OK):
            raise InputError("The file is not accessible. Please check read permissions.")

    @staticmethod
    def validate_place_entry(place):
        if not place:
            raise InputError("The place field (URL or Path) is empty. Please provide a valid place.")
