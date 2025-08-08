# views/main_view.py
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.ttk import Label, Button, Combobox, Frame, Scrollbar

from ..viewmodels.flasher_vm import AutoFlasherViewModel
from ..utils import write_log
import os

SUPPORTED_TARGETS = ("IO", "Delsys", "Logo")

class AutoFlasherApp:
    """Tk 'View' layer. No business logic lives here—it's all in the ViewModel."""

    def __init__(self, root: tk.Tk, base_dir: str):
        self.root = root
        self.base_dir = base_dir

        self.root.title("AcclaroMD AutoFlasher Utility")
        self.root.geometry("620x410")

        # --- ViewModel ---
        self.vm = AutoFlasherViewModel(self.base_dir)
        self.vm.on_status = self._on_status
        self.vm.on_log = self._on_log
        self.vm.on_completed = self._on_completed

        # --- Folder list from VM (scoped to firmware_root) ---
        self.list_folders = self.vm.list_folders()

        # === Folder Selection ===
        Label(self.root, text="Select Folder:").pack(pady=(20, 5))
        self.selected_folder = tk.StringVar()
        self.combo_folder = Combobox(self.root, textvariable=self.selected_folder, state="readonly")
        self.combo_folder["values"] = self.list_folders
        self._apply_default_folder()
        self.combo_folder.pack(pady=(0, 12))

        # === Target Selection ===
        Label(self.root, text="Select Target:").pack(pady=(5, 5))
        self.selected_target = tk.StringVar()
        self.combo_target = Combobox(self.root, textvariable=self.selected_target, state="readonly")
        self.combo_target["values"] = SUPPORTED_TARGETS
        self._apply_default_target()
        self.combo_target.pack(pady=(0, 12))

        # === Buttons ===
        self.flash_button = Button(self.root, text="Flash", command=self.on_flash)
        self.flash_button.pack(pady=8)

        self.config_button = Button(self.root, text="Edit Settings...", command=self.open_config_editor)
        self.config_button.pack(pady=(0, 10))

        # === Status ===
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor="w", fg="blue")
        self.status_label.pack(fill="x", padx=10, pady=(0, 5))

        # === Collapsible Log (create BEFORE first status) ===
        self.log_visible = False
        self.toggle_log_button = Button(self.root, text="Show Log ▼", command=self.toggle_log)
        self.toggle_log_button.pack(fill="x", padx=10, pady=(0, 2))

        self.log_frame = Frame(self.root)
        self.log_text = tk.Text(
            self.log_frame, wrap="word", height=10, state="disabled",
            bg="#222", fg="#eee", font=("Consolas", 10)
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        self.scrollbar = Scrollbar(self.log_frame, command=self.log_text.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=self.scrollbar.set)

        # Initial status
        self._on_status(f"Using J-Link at: {self.vm.jlink_path}", False)

    # ===== VM event handlers =====
    def _on_status(self, msg: str, is_error: bool):
        self.status_var.set(msg)
        self.status_label.config(fg="red" if is_error else "blue")
        write_log(self.log_text, msg, is_error)

    def _on_log(self, msg: str, is_error: bool):
        write_log(self.log_text, msg, is_error)

    def _on_completed(self, outcome):
        if outcome.success:
            messagebox.showinfo("Success", "Flashing completed successfully!")
        else:
            details = "\n- ".join(outcome.errors[:6]) if outcome.errors else "Unknown error."
            messagebox.showerror("Flash Failed", f"Flash failed.\n\n- {details}")
        self.flash_button.config(state="normal")

    # ===== UI actions =====
    def toggle_log(self):
        if self.log_visible:
            self.log_frame.pack_forget()
            self.toggle_log_button.config(text="Show Log ▼")
        else:
            self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.toggle_log_button.config(text="Hide Log ▲")
        self.log_visible = not self.log_visible

    def on_flash(self):
        self.flash_button.config(state="disabled")
        self.vm.flash_async(self.selected_folder.get(), self.selected_target.get())

    # ===== defaults from config =====
    def _apply_default_folder(self):
        default = (self.vm.config.get("default_folder") or "").strip()
        matched = next((f for f in self.list_folders if f.lower() == default.lower()), None)
        if matched:
            self.combo_folder.set(matched)
        elif self.list_folders:
            self.combo_folder.current(0)

    def _apply_default_target(self):
        default = (self.vm.config.get("default_target") or "").strip()
        matched = next((t for t in SUPPORTED_TARGETS if t.lower() == default.lower()), None)
        if matched:
            self.combo_target.set(matched)
        else:
            self.combo_target.current(0)

    # ===== Config editor =====
    def open_config_editor(self):
        cfg = self.vm.get_config()

        top = tk.Toplevel(self.root)
        top.title("Edit Configuration")
        top.geometry("460x470")
        top.grab_set()  # modal

        # J-Link path
        tk.Label(top, text="J-Link Executable Path:").pack(anchor="w", padx=12, pady=(15, 2))
        jlink_var = tk.StringVar(value=cfg.get("jlink_path", ""))
        tk.Entry(top, textvariable=jlink_var, width=48).pack(anchor="w", padx=12)

        def browse_jlink():
            exe = filedialog.askopenfilename(
                title="Select J-Link Executable",
                filetypes=[("Executable", "*.exe;*.*")] if os.name == "nt" else [("All files", "*.*")]
            )
            if exe:
                jlink_var.set(exe)

        Button(top, text="Browse...", command=browse_jlink).pack(anchor="w", padx=12, pady=(2, 10))

        # Interface
        tk.Label(top, text="J-Link Interface:").pack(anchor="w", padx=12)
        interface_var = tk.StringVar(value=cfg.get("jlink_interface", "SWD"))
        interface_combo = Combobox(top, textvariable=interface_var, state="readonly", width=16)
        interface_combo["values"] = ("SWD", "JTAG")
        interface_combo.pack(anchor="w", padx=12, pady=(0, 8))

        # Speed
        tk.Label(top, text="J-Link Speed (kHz):").pack(anchor="w", padx=12)
        speed_var = tk.StringVar(value=str(cfg.get("jlink_speed", 4000)))
        tk.Entry(top, textvariable=speed_var, width=16).pack(anchor="w", padx=12, pady=(0, 8))

        # Firmware root (subfolder under app dir)
        tk.Label(top, text="Firmware Root Folder (relative):").pack(anchor="w", padx=12)
        fw_root_var = tk.StringVar(value=cfg.get("firmware_root", "firmware"))
        tk.Entry(top, textvariable=fw_root_var, width=28).pack(anchor="w", padx=12, pady=(0, 8))

        # Firmware extensions (comma-separated)
        tk.Label(top, text="Firmware Extensions (e.g. .axf,.elf,.bin):").pack(anchor="w", padx=12)
        fw_exts_var = tk.StringVar(value=",".join(cfg.get("firmware_exts", [])))
        tk.Entry(top, textvariable=fw_exts_var, width=38).pack(anchor="w", padx=12, pady=(0, 8))

        # Default folder
        tk.Label(top, text="Default Folder:").pack(anchor="w", padx=12)
        folder_var = tk.StringVar(value=cfg.get("default_folder", ""))
        folder_combo = Combobox(top, textvariable=folder_var, state="readonly", width=28)
        folder_combo["values"] = self.list_folders
        folder_combo.pack(anchor="w", padx=12, pady=(0, 8))

        # Default target
        tk.Label(top, text="Default Target:").pack(anchor="w", padx=12)
        target_var = tk.StringVar(value=cfg.get("default_target", ""))
        target_combo = Combobox(top, textvariable=target_var, state="readonly", width=20)
        target_combo["values"] = SUPPORTED_TARGETS
        target_combo.pack(anchor="w", padx=12, pady=(0, 16))

        # Buttons
        btns = tk.Frame(top)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        def save_changes():
            try:
                speed_val = int(speed_var.get())
                if speed_val <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Invalid Input", "J-Link Speed must be a positive integer.", parent=top)
                return

            raw_exts = [e.strip() for e in fw_exts_var.get().split(",") if e.strip()]
            norm_exts = [(e if e.startswith(".") else f".{e}") for e in raw_exts]

            self.vm.save_config(
                jlink_path=jlink_var.get(),
                interface=interface_var.get(),
                speed_khz=speed_val,
                default_folder=folder_var.get(),
                default_target=target_var.get(),
                firmware_root=fw_root_var.get(),
                firmware_exts=norm_exts,
            )

            self.list_folders = self.vm.list_folders()
            self.combo_folder["values"] = self.list_folders
            self._apply_default_folder()
            self._apply_default_target()

            top.destroy()

        Button(btns, text="Cancel", command=top.destroy, width=10).pack(side="right", padx=6)
        Button(btns, text="Save", command=save_changes, width=10).pack(side="right")
