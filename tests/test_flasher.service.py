import os
import types
import pytest

from AutoFlasher.flasher_service import FlasherService, DEVICE_LINES
from AutoFlasher.models import FlashOutcome

# Sample outputs (trimmed to essentials)
OUTPUT_SUCCESS = """
Connecting to target via SWD
InitTarget() start
J-Link>loadfile "C:\\file.axf" 0x0
J-Link: Flash download: Program & Verify: ...
O.K.
J-Link>exit
"""

OUTPUT_VOLTAGE_LOW = """
Connecting to target via SWD
Target voltage too low. Please check https://wiki.segger.com/J-Link_cannot_connect_to_the_CPU#Target_connection.
Error occurred: Could not connect to the target device.
J-Link>exit
"""

OUTPUT_RAMCODE_FAIL = """
****** Error: Verification of RAMCode failed @ address 0x1FFFE000.
Failed to prepare for programming.
Failed to download RAMCode!
Unspecified error -1
J-Link>exit
"""

def make_service(tmp_path, jlink_path="JLink.exe"):
    # Base dir can be a temporary empty folder; we don't touch disk in these tests
    return FlasherService(
        base_dir=str(tmp_path),
        jlink_path=jlink_path,
        interface="SWD",
        speed_khz=4000,
    )

def test_analyze_output_success(tmp_path):
    svc = make_service(tmp_path)
    outcome: FlashOutcome = svc.analyze_output(OUTPUT_SUCCESS)
    assert outcome.success is True
    assert not outcome.errors

def test_analyze_output_voltage_low(tmp_path):
    svc = make_service(tmp_path)
    outcome: FlashOutcome = svc.analyze_output(OUTPUT_VOLTAGE_LOW)
    assert outcome.success is False
    assert any("Target voltage too low" in e for e in outcome.errors)

def test_analyze_output_ramcode_failed(tmp_path):
    svc = make_service(tmp_path)
    outcome: FlashOutcome = svc.analyze_output(OUTPUT_RAMCODE_FAIL)
    assert outcome.success is False
    assert any("Verification of RAMCode failed" in e for e in outcome.errors)

def test_build_script_uses_comment_command(tmp_path):
    svc = make_service(tmp_path)
    script = svc.build_script(target="IO", firmware_file="C:/firm.axf")
    # J-Link comments should be '//' not '#'
    assert "// Program IFR FOPT field (IO only)" in script
    # baseline
    assert "loadfile" in script
    assert DEVICE_LINES["IO"] in script
