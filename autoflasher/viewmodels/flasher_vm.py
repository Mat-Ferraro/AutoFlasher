# view_model.py
from __future__ import annotations

import os
import threading
from typing import Callable, Optional, List, Any

from autoflasher.config_service import load_config, save_config, JLINK_WINDOWS, JLINK_UNIX
from autoflasher.flasher_service import FlasherService
from ..models.firmware_models import FlashOutcome


class AutoFlasherViewModel:
    """
    UI-agnostic application logic (the ViewModel in MVVM).

    Responsibilities:
      - Load/save configuration
      - Create and manage FlasherService (script build/run/analyze)
      - Expose async 'flash' command
      - Emit status/log/completion events for the View to render

    The View should set these callbacks (all optional):
      - on_status:   Callable[[str, bool], None]      # (message, is_error)
      - on_log:      Callable[[str, bool], None]      # (message, is_error)
      - on_completed:Callable[[FlashOutcome], None]
    """

    # ---------- lifecycle ----------
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.config = load_config(base_dir)

        # public events (the View may assign these)
        self.on_status: Optional[Callable[[str, bool], None]] = None
        self.on_log: Optional[Callable[[str, bool], None]] = None
        self.on_completed: Optional[Callable[[FlashOutcome], None]] = None

        # compute current J-Link path & build service
        self.jlink_path = self._resolve_jlink_path()
        self._svc = self._make_service()

    # ---------- helpers ----------
    def _emit_status(self, msg: str, is_error: bool = False) -> None:
        if self.on_status:
            self.on_status(msg, is_error)
        if self.on_log:
            self.on_log(msg, is_error)

    def _resolve_jlink_path(self) -> str:
        """Choose jlink_path from config or OS-specific default."""
        p = self.config.get("jlink_path", "").strip()
        return p or (JLINK_WINDOWS if os.name == "nt" else JLINK_UNIX)

    def _make_service(self) -> FlasherService:
        """Create a FlasherService instance based on current config."""
        firmware_root = self.config.get("firmware_root", "firmware")
        exts: Optional[List[str]] = self.config.get("firmware_exts")
        try:
            # Normalize extensions if provided (ensure they start with a dot)
            if isinstance(exts, list):
                exts = [e if e.startswith(".") else f".{e}" for e in exts]
        except Exception:
            exts = None

        return FlasherService(
            base_dir=self.base_dir,
            jlink_path=self.jlink_path,
            interface=self.config.get("jlink_interface", "SWD"),
            speed_khz=int(self.config.get("jlink_speed", 4000)),
            firmware_root=firmware_root,
            allowed_exts=exts,
        )

    # ---------- queries ----------
    def list_folders(self) -> List[str]:
        """Folders under the configured firmware_root."""
        return self._svc.list_local_folders()

    def get_config(self) -> dict:
        """Return the live config dict (for binding/editors)."""
        return self.config

    # ---------- commands ----------
    def flash_async(self, folder: str, target: str) -> None:
        """Kick off flashing in a background thread."""
        t = threading.Thread(target=self._flash_worker, args=(folder, target), daemon=True)
        t.start()

    def _flash_worker(self, folder: str, target: str) -> None:
        """Actual flashing flow; runs off the UI thread."""
        if not folder or not target:
            self._emit_status("Both folder and target must be selected.", True)
            if self.on_completed:
                self.on_completed(FlashOutcome(False, ["Missing selections."], []))
            return

        self._emit_status("Searching for firmware file...")
        search_tag = f"_{target.lower()}_"
        fw_path = self._svc.find_firmware_file(folder, search_tag)
        if not fw_path:
            msg = f"No file containing '{search_tag}' found in {folder}"
            self._emit_status(msg, True)
            if self.on_completed:
                self.on_completed(FlashOutcome(False, [msg], []))
            return

        self._emit_status("Building J-Link script...")
        script = self._svc.build_script(target, fw_path)

        self._emit_status("Flashing device. Please wait...")
        try:
            out = self._svc.run_script(script)
            if self.on_log:
                self.on_log("--- J-Link output ---\n" + (out or ""), False)
            outcome = self._svc.analyze_output(out)
        except Exception as e:
            outcome = FlashOutcome(False, [str(e)], [], "")

        # Emit a summary status and completion event
        if outcome.success:
            self._emit_status("Flashing completed successfully!", False)
        else:
            self._emit_status("Flash appears to have failed.", True)

        if self.on_completed:
            self.on_completed(outcome)

    # ---------- configuration ----------
    def save_config(
        self,
        *,
        jlink_path: str,
        interface: str,
        speed_khz: int,
        default_folder: str,
        default_target: str,
        firmware_root: str,
        firmware_exts: Optional[List[str]] = None,
    ) -> None:
        """
        Persist configuration and reinitialize service.
        Some settings (like path/interface/speed/firmware root) take effect immediately.
        """
        # update in-memory config
        self.config["jlink_path"] = (jlink_path or "").strip()
        self.config["jlink_interface"] = (interface or "SWD").strip()
        self.config["jlink_speed"] = int(speed_khz or 4000)
        self.config["default_folder"] = (default_folder or "").strip()
        self.config["default_target"] = (default_target or "").strip()
        self.config["firmware_root"] = (firmware_root or "firmware").strip()

        if isinstance(firmware_exts, list):
            # normalize to '.ext' strings
            norm_exts = []
            for e in firmware_exts:
                if not e:
                    continue
                e = e.strip()
                if not e:
                    continue
                norm_exts.append(e if e.startswith(".") else f".{e}")
            self.config["firmware_exts"] = norm_exts
        elif "firmware_exts" in self.config:
            # keep existing if not provided, or delete if explicitly None
            if firmware_exts is None:
                pass

        # persist to disk
        save_config(self.base_dir, self.config)

        # hot-apply: rebuild path + service
        self.jlink_path = self._resolve_jlink_path()
        self._svc = self._make_service()

        self._emit_status("Configuration saved. Some changes apply immediately.", False)
