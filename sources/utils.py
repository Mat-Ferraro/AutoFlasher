# utils.py

def write_log(text_widget, message: str, is_error: bool = False) -> None:
    """Append a line to the GUI log window, auto-scroll, and colorize."""
    if text_widget is None:
        return
    text_widget.config(state="normal")
    tag = "error" if is_error else "info"
    text_widget.insert("end", (message or "").rstrip() + "\n", tag)
    text_widget.see("end")
    text_widget.config(state="disabled")
    # Configure tags once
    if "error" not in text_widget.tag_names():
        text_widget.tag_configure("error", foreground="red")
        text_widget.tag_configure("info", foreground="#eee")
