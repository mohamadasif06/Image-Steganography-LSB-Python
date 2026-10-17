"""Python equivalents of the C project's user-defined types."""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Status(Enum):
    e_failure = 0
    e_success = 1

class OperationType(Enum):
    e_encode = "-e"
    e_decode = "-d"
    e_scan = "-s"
    e_unsupported = "unsupported"

@dataclass
class EncodeInfo:
    src_image_fname: str = ""
    secret_fname: str = ""
    stego_image_fname: str = "stego.bmp"
    image_capacity: int = 0
    extn_secret_file: str = ""
    size_secret_file: int = 0

@dataclass
class DecodeInfo:
    stego_image_fname: str = ""
    output_fname: str = ""
    extn_secret_file: str = ""
    size_secret_file: int = 0
