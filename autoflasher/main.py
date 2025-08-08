# main.py
import sys
import traceback
import tkinter as tk
from tkinter import messagebox
from .main_view import AutoFlasherApp  # relative import works when run as module/package
from autoflasher import config_service
import os 

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
config = config_service.load_config(APP_ROOT)
firmware_root = os.path.join(APP_ROOT, config.get("firmware_root", "firmware"))

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
