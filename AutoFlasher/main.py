# main.py
import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
from .gui import AutoFlasherApp  # relative import works when run as module/package

def run() -> None:
    root = tk.Tk()
    app = AutoFlasherApp(root)
    root.mainloop()

def main() -> None:
    try:
        run()
    except Exception as e:
        # Show a concise dialog and also print the full traceback to stderr
        try:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            print(tb, file=sys.stderr)
            messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n\n{e}")
        except Exception:
            # If Tk/messagebox fails for some reason, at least print the error
            print("Fatal Error:", e, file=sys.stderr)
        raise  # re-raise so external runners/CI can detect failure

if __name__ == "__main__":
    main()
