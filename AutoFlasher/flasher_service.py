import os
import logging
from .jlink_commands import (
    SuppressGuiCommand, DeviceCommand, InterfaceCommand, SpeedCommand,
    ConnectCommand, UnlockKinetisCommand, ResetCommand, EraseCommand,
    WriteRegisterCommand, SleepCommand, LoadFileCommand, CommentCommand,
    GoCommand, ExitCommand
)


class FlasherService:
    def __init__(self, config, firmware_root="firmware"):
        self.config = config

        # Determine paths relative to project root, not the autoflasher package
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(package_dir)

        if os.path.isabs(firmware_root):
            self.firmware_root = firmware_root
        else:
            self.firmware_root = os.path.join(project_root, firmware_root)

        # Ensure firmware directory exists
        if not os.path.exists(self.firmware_root):
            logging.warning(f"Firmware root directory not found: {self.firmware_root}")

    def list_firmware_folders(self):
        """Return a list of subdirectories inside the firmware root."""
        try:
            return [
                name for name in os.listdir(self.firmware_root)
                if os.path.isdir(os.path.join(self.firmware_root, name))
            ]
        except FileNotFoundError:
            logging.error(f"Firmware root not found: {self.firmware_root}")
            return []

    def find_firmware_file(self, folder, search_tag):
        """Find a firmware file containing the search_tag in its name."""
        folder_path = os.path.join(self.firmware_root, folder)
        try:
            for file in os.listdir(folder_path):
                if search_tag.lower() in file.lower():
                    return os.path.join(folder_path, file)
        except FileNotFoundError:
            logging.error(f"Firmware folder not found: {folder_path}")
        return None

    def get_device_line(self, target):
        """Return the device line from config based on the target."""
        device_map = {
            "IO": "Device K32L3Axxxxxxxx_M4",
            "DELSYS": "Device K32L2B31xxxxA",
            "LOGO": "Device K32L2B31xxxxA"
        }
        return device_map.get(target.upper(), "")

    def build_jlink_script(self, device_line, firmware_file, is_io):
        """Build the J-Link command list."""
        commands = [
            SuppressGuiCommand(),
            DeviceCommand(device_line),
            InterfaceCommand(self.config.get("interface", "SWD")),
            SpeedCommand(self.config.get("speed", 4000)),
            ConnectCommand()
        ]

        if is_io:
            commands.append(UnlockKinetisCommand())

        commands.extend([
            ResetCommand(),
            EraseCommand(),
            WriteRegisterCommand(4, 0x40023004, 0x44000000),
            WriteRegisterCommand(1, 0x40023000, 0x70),
            WriteRegisterCommand(1, 0x40023000, 0x80),
            SleepCommand(5),
            LoadFileCommand(firmware_file)
        ])

        if is_io:
            commands.extend([
                CommentCommand("Program IFR FOPT field (IO only)"),
                WriteRegisterCommand(4, 0x40023004, 0x43840000),
                WriteRegisterCommand(4, 0x40023008, 0xFFFFF3FF),
                WriteRegisterCommand(1, 0x40023000, 0x70),
                WriteRegisterCommand(1, 0x40023000, 0x80),
                SleepCommand(5)
            ])

        commands.extend([
            ResetCommand(),
            GoCommand(),
            ExitCommand()
        ])

        return "\n".join(cmd.render() for cmd in commands)

    def run_jlink_script(self, script_content):
        """Execute the J-Link script and return its output."""
        import subprocess
        import tempfile

        jlink_path = self.config.get("jlink_path")
        if not jlink_path:
            raise RuntimeError("J-Link path is not configured.")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jlink") as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            process = subprocess.run(
                [jlink_path, "-CommanderScript", script_path],
                capture_output=True, text=True
            )
            return process.stdout + "\n" + process.stderr
        finally:
            os.remove(script_path)
