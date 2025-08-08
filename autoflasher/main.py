import sys
import traceback
import tkinter as tk
from tkinter import messagebox
from .views.main_view import AutoFlasherApp
from autoflasher import config_service
import os 

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

def run() -> None:
    root = tk.Tk()
    app = AutoFlasherApp(root, base_dir=APP_ROOT)   # Pass the real base_dir!
    root.mainloop()

def main() -> None:
    try:
        run()
    except Exception as e:
        try:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            print(tb, file=sys.stderr)
            messagebox.showerror("Fatal Error", f"An unexpected error occurred:\n\n{e}")
        except Exception:
            print("Fatal Error:", e, file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
