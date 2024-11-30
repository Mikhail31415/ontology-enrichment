import tkinter as tk
from tkinter import ttk


class ErrorWindow:
    def __init__(self, root, error_message):
        self.error_win = tk.Toplevel(root)
        self.error_win.title("Error")
        self.error_win.geometry("400x300")
        self.error_win.resizable(True, True)


        self.error_win.update_idletasks()
        screen_width = self.error_win.winfo_screenwidth()
        screen_height = self.error_win.winfo_screenheight()
        window_width = self.error_win.winfo_width()
        window_height = self.error_win.winfo_height()

        center_x = int((screen_width - window_width) / 2)
        center_y = int((screen_height - window_height) / 2)
        self.error_win.geometry(f"+{center_x}+{center_y}")

        text_frame = ttk.Frame(self.error_win)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        label = ttk.Label(text_frame, text="Error:", font=("Arial", 12, "bold"))
        label.pack(anchor=tk.W, pady=(0, 5))

        text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        message_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=text_scrollbar.set,
            height=10,
            font=("Arial", 10),
        )
        message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scrollbar.config(command=message_text.yview)

        message_text.insert(tk.END, error_message)
        message_text.configure(state=tk.DISABLED)

        button_frame = ttk.Frame(self.error_win)
        button_frame.pack(fill=tk.X, pady=10)

        ok_button = ttk.Button(button_frame, text="OK", command=self.error_win.destroy)
        ok_button.pack(pady=10, side=tk.BOTTOM)

        self.error_win.columnconfigure(0, weight=1)
        self.error_win.rowconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.error_win.transient(root)
        self.error_win.grab_set()
        root.wait_window(self.error_win)
