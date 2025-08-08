# jlink_commands.py

class JLinkCommand:
    def render(self) -> str:
        raise NotImplementedError()

class SuppressGuiCommand(JLinkCommand):
    def render(self): return "SuppressGUI 1"

class DeviceCommand(JLinkCommand):
    def __init__(self, device_line): self.device_line = device_line
    def render(self): return self.device_line

class InterfaceCommand(JLinkCommand):
    def __init__(self, interface): self.interface = interface
    def render(self): return f"IF {self.interface}"

class SpeedCommand(JLinkCommand):
    def __init__(self, speed): self.speed = speed
    def render(self): return f"Speed {self.speed}"

class ConnectCommand(JLinkCommand):
    def render(self): return "connect"

class UnlockKinetisCommand(JLinkCommand):
    def render(self): return "unlock kinetis"

class ResetCommand(JLinkCommand):
    def render(self): return "r"

class EraseCommand(JLinkCommand):
    def render(self): return "erase"

class WriteRegisterCommand(JLinkCommand):
    def __init__(self, width, addr, value):
        self.width = width
        self.addr = addr
        self.value = value
    def render(self): return f"w{self.width} 0x{self.addr:08X}, 0x{self.value:08X}"

class SleepCommand(JLinkCommand):
    def __init__(self, seconds): self.seconds = seconds
    def render(self): return f"Sleep {self.seconds}"

class LoadFileCommand(JLinkCommand):
    def __init__(self, file_path): self.file_path = file_path
    def render(self): return f'loadfile "{self.file_path}" 0x0'

class CommentCommand(JLinkCommand):
    def __init__(self, comment): self.comment = comment
    def render(self): return f"// {self.comment}"   # <-- use '//' not '#'

class GoCommand(JLinkCommand):
    def render(self): return "g"

class ExitCommand(JLinkCommand):
    def render(self): return "exit"
