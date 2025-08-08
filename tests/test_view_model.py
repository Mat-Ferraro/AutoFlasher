import pytest

from AutoFlasher.view_model import AutoFlasherViewModel
from AutoFlasher.models import FlashOutcome

SUCCESS_OUT = """
J-Link>loadfile "C:\\file.axf" 0x0
J-Link: Flash download: Program & Verify: ...
O.K.
J-Link>exit
"""

FAIL_OUT = """
Connecting to target via SWD
Target voltage too low. Please check ...
Error occurred: Could not connect to the target device.
J-Link>exit
"""

class DummySvc:
    """A fake FlasherService to drive the ViewModel logic without real J-Link."""
    def __init__(self):
        self.ran = False
        self.base_dir = "X:/fake"

    def list_local_folders(self):
        return ["FolderA", "FolderB"]

    def find_firmware_file(self, folder, search_tag):
        # Pretend we always find a file for tests
        return f"{self.base_dir}/{folder}/firmware{search_tag}.axf"

    def build_script(self, target, fw):
        return f"// script for {target} -> {fw}"

    def run_script(self, script_text):
        self.ran = True
        return SUCCESS_OUT

    # Provide the same interface as real service
    def analyze_output(self, text):
        if "Target voltage too low" in text:
            return FlashOutcome(False, ["Target voltage too low"], [])
        if "O.K." in text:
            return FlashOutcome(True, [], [])
        return FlashOutcome(False, ["Unknown error"], [])

def make_vm(monkeypatch, base_dir, svc_factory):
    vm = AutoFlasherViewModel(base_dir)
    # Swap out the real service with our dummy/mocked one
    svc = svc_factory()
    vm.svc = svc
    vm.config.update({
        "default_folder": "FolderA",
        "default_target": "IO",
        "jlink_speed": 4000,
        "jlink_interface": "SWD",
        "jlink_path": "JLink.exe",
    })
    return vm, svc

def test_vm_success_path(monkeypatch, tmp_path):
    vm, svc = make_vm(monkeypatch, str(tmp_path), lambda: DummySvc())

    events = {"status": [], "completed": []}
    vm.on_status = lambda msg, err=False: events["status"].append((msg, err))
    vm.on_log = lambda msg, err=False: None
    vm.on_completed = lambda outcome: events["completed"].append(outcome)

    # call the worker directly (no threads in tests)
    vm._flash_worker("FolderA", "IO")

    assert svc.ran is True
    assert events["completed"], "Expected completion callback"
    assert events["completed"][0].success is True
    # Ensure we produced a success status at some point
    assert any("completed successfully" in s[0].lower() for s in events["status"])

def test_vm_failure_path(monkeypatch, tmp_path):
    class FailingSvc(DummySvc):
        def run_script(self, script_text):
            self.ran = True
            return FAIL_OUT

    vm, svc = make_vm(monkeypatch, str(tmp_path), lambda: FailingSvc())

    events = {"status": [], "completed": []}
    vm.on_status = lambda msg, err=False: events["status"].append((msg, err))
    vm.on_log = lambda msg, err=False: None
    vm.on_completed = lambda outcome: events["completed"].append(outcome)

    vm._flash_worker("FolderA", "IO")

    assert svc.ran is True
    assert events["completed"], "Expected completion callback"
    assert events["completed"][0].success is False
    # Ensure we produced an error status
    assert any(err for (_, err) in events["status"]), "Expected at least one error status"
