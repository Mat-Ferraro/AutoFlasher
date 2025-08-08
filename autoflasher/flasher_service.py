# flasher_service.py
import os
import re
import tempfile
import subprocess
from typing import List, Optional

from autoflasher.jlink_commands import (
    DeviceCommand, InterfaceCommand, SpeedCommand,
    ConnectCommand, UnlockKinetisCommand, ResetCommand, EraseCommand,
    WriteRegisterCommand, SleepCommand, LoadFileCommand, CommentCommand,
    GoCommand, ExitCommand
)

DEVICE_LINES = {
    "IO": "Device K32L3Axxxxxxxx_M4",
    "DELSYS": "Device K32L2B31xxxxA",
    "LOGO": "Device K32L2B31xxxxA",
}

DEFAULT_FIRMWARE_EXTS = (".axf", ".elf", ".bin", ".hex", ".s19", ".srec")


class FlashOutcome:
    """Result of a flash attempt: success flag, errors/warnings, and the raw J-Link output."""
    def __init__(self, success: bool, errors: Optional[List[str]] = None,
                 warnings: Optional[List[str]] = None, raw_output: str = ""):
        self.success = success
        self.errors = errors or []
        self.warnings = warnings or []
        self.raw_output = raw_output

    def __bool__(self):
        return self.success


class FlasherService:
    def __init__(
        self,
        base_dir: str,
        jlink_path: str,
        interface: str = "SWD",
        speed_khz: int = 4000,
        firmware_root: str = "firmware",
        allowed_exts: Optional[List[str]] = None,
    ) -> None:
        self.base_dir = base_dir
        self.jlink_path = jlink_path
        self.interface = interface
        self.speed_khz = int(speed_khz)

        # Project root is one level up from package dir
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(package_dir)
        if os.path.isabs(firmware_root):
            self.firmware_root = firmware_root
        else:
            self.firmware_root = os.path.join(project_root, firmware_root or "firmware")

        self.allowed_exts = tuple((allowed_exts or DEFAULT_FIRMWARE_EXTS))
        os.makedirs(self.firmware_root, exist_ok=True)

    def _is_valid_folder_name(self, name: str) -> bool:
        bad = {"__pycache__", ".git", ".vscode", ".idea", "venv", "env", ".pytest_cache", "dist", "build"}
        if not name:
            return False
        if name in bad or name.startswith(".") or name.startswith("_"):
            return False
        return True

    def list_local_folders(self) -> List[str]:
        try:
            entries = os.listdir(self.firmware_root)
        except FileNotFoundError:
            return []
        return [
            n
            for n in entries
            if self._is_valid_folder_name(n) and os.path.isdir(os.path.join(self.firmware_root, n))
        ]

    def find_firmware_file(self, folder: str, search_tag: str) -> Optional[str]:
        folder_path = os.path.join(self.firmware_root, folder)
        try:
            for name in os.listdir(folder_path):
                lower = name.lower()
                if search_tag in lower and lower.endswith(self.allowed_exts):
                    return os.path.join(folder_path, name)
        except FileNotFoundError:
            return None
        return None

    def get_device_line(self, target: str) -> str:
        return DEVICE_LINES.get(target.upper(), DEVICE_LINES["IO"])

    def build_script(self, target: str, firmware_file: str) -> str:
        is_io = target.upper() == "IO"
        cmds = [
            DeviceCommand(self.get_device_line(target)),
            InterfaceCommand(self.interface),
            SpeedCommand(self.speed_khz),
            ConnectCommand(),
            UnlockKinetisCommand(),
            ResetCommand(),
            EraseCommand(),
            WriteRegisterCommand(4, 0x40023004, 0x44000000),
            WriteRegisterCommand(1, 0x40023000, 0x70),
            WriteRegisterCommand(1, 0x40023000, 0x80),
            SleepCommand(5),
            LoadFileCommand(firmware_file),
        ]
        if is_io:
            cmds += [
                CommentCommand("Program IFR FOPT field (IO only)"),
                WriteRegisterCommand(4, 0x40023004, 0x43840000),
                WriteRegisterCommand(4, 0x40023008, 0xFFFFF3FF),
                WriteRegisterCommand(1, 0x40023000, 0x70),
                WriteRegisterCommand(1, 0x40023000, 0x80),
                SleepCommand(5),
            ]
        cmds += [
            ResetCommand(), 
            GoCommand(), 
            ExitCommand()
            ]  
        return "\n".join(c.render() for c in cmds)

    def run_script(self, script_text: str) -> str:
        """Executes the J-Link Commander script and returns its combined stdout/stderr."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jlink", mode="w", encoding="utf-8") as f:
            f.write(script_text)
            script_path = f.name
        try:
            proc = subprocess.run(
                [self.jlink_path, "-CommandFile", script_path],
                capture_output=True, text=True, shell=True
            )
            return (proc.stdout or "") + (proc.stderr or "")
        finally:
            try:
                os.remove(script_path)
            except Exception:
                pass

    def analyze_output(self, text: str) -> FlashOutcome:
        """
        Heuristically determine success/failure from J-Link Commander output.
        Success criteria:
          - A 'loadfile' command was issued, AND
          - At least one 'O.K.' string after programming (case insensitive), AND
          - No error patterns matched.
        """
        if not text:
            return FlashOutcome(False, ["No output from J-Link."], [], "")

        t = text.strip()

        # Fatal errors
        error_patterns = [
            r"Target voltage too low",
            r"Could not connect to the target device",
            r"Error occurred:.*",
            r"Unspecified error\b",
            r"Failed to prepare for programming",
            r"Failed to download RAMCode",
            r"Verification of RAMCode failed",
            r"Cannot connect",
            r"Connection failed",
            r"Cannot identify target",
            r"J-Link.*error",
            r"Error:",
        ]

        errors: List[str] = []
        for pat in error_patterns:
            for m in re.finditer(pat, t, re.IGNORECASE):
                errors.append(m.group(0))
        if errors:
            return FlashOutcome(False, errors, [], text)

        # Must see a 'loadfile' command
        if "loadfile" not in t.lower():
            return FlashOutcome(False, ["No 'loadfile' found in output."], [], text)

        # Must see at least one O.K. or Program speed (case-insensitive)
        if re.search(r"O\.K\.", t, re.IGNORECASE):
            return FlashOutcome(True, [], [], text)
        if re.search(r"Program\s*&\s*Verify", t, re.IGNORECASE) or re.search(r"Program speed", t, re.IGNORECASE):
            return FlashOutcome(True, [], [], text)

        # Fallback: fail if nothing matched
        return FlashOutcome(False, ["No success marker ('O.K.') found in output."], [], text)
