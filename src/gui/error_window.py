import tkinter as tk
from tkinter import ttk


class ErrorWindow:
    def __init__(self, root, error_message):
        self.error_win = tk.Toplevel(root)
        self.error_win.title("Error")
        self.error_win.geometry("300x150")
        self.error_win.resizable(False, False)


        self.error_win.update_idletasks()
        screen_width = self.error_win.winfo_screenwidth()
        screen_height = self.error_win.winfo_screenheight()
        window_width = self.error_win.winfo_width()
        window_height = self.error_win.winfo_height()

        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)

        self.error_win.geometry(f"+{center_x}+{center_y}")

        label = ttk.Label(self.error_win, text="Error:", font=("Arial", 12, "bold"))
        label.pack(pady=(10, 0))

        message_label = ttk.Label(self.error_win, text=error_message, wraplength=280)
        message_label.pack(pady=10, padx=10)

        ok_button = ttk.Button(self.error_win, text="OK", command=self.error_win.destroy)
        ok_button.pack(pady=10)

        self.error_win.transient(root)
        self.error_win.grab_set()
        root.wait_window(self.error_win)
