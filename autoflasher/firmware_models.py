# models.py
from dataclasses import dataclass
from typing import List

@dataclass
class FlashOutcome:
    success: bool
    errors: List[str]
    warnings: List[str]
    raw_output: str = ""
