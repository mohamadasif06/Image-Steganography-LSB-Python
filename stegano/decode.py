"""Decoding functions for the C-project-style BMP LSB format."""
from pathlib import Path
import re
import struct
from .common import MAGIC_STRING, BMP_HEADER_MIN_SIZE
from .encode import SteganoError, _read_bmp
from .types import DecodeInfo, Status

_U32 = struct.Struct(">I")
_EXT_RE = re.compile(rb"^\.[A-Za-z0-9]{1,12}$")

def _extract_bytes(carriers, start, count):
    if count < 0 or start < 0 or start + count * 8 > len(carriers):
        raise SteganoError("Image does not contain a complete hidden message.")
    output = bytearray()
    for byte_index in range(count):
        value = 0
        base = start + byte_index * 8
        for bit_index in range(8):
            value = (value << 1) | (carriers[base + bit_index] & 1)
        output.append(value)
    return bytes(output)

def decode_size_from_lsb(carriers, start):
    return _U32.unpack(_extract_bytes(carriers, start, 4))[0]

def extract_hidden_file(image_path):
    """Return (payload bytes, extension) or raise if the marker/metadata is invalid."""
    image_data, pixel_offset, pixel_size = _read_bmp(image_path)
    carriers = image_data[pixel_offset:pixel_offset + pixel_size]
    marker = _extract_bytes(carriers, 0, len(MAGIC_STRING))
    if marker != MAGIC_STRING:
        raise SteganoError("Marker not found.")
    position = len(MAGIC_STRING) * 8
    extension_size = decode_size_from_lsb(carriers, position)
    position += 32
    if not 1 <= extension_size <= 16:
        raise SteganoError("Invalid hidden file extension size.")
    extension = _extract_bytes(carriers, position, extension_size)
    position += extension_size * 8
    if not _EXT_RE.fullmatch(extension):
        raise SteganoError("Hidden file extension is invalid.")
    file_size = decode_size_from_lsb(carriers, position)
    position += 32
    if file_size * 8 > len(carriers) - position:
        raise SteganoError("Hidden file size exceeds image capacity or data is incomplete.")
    payload = _extract_bytes(carriers, position, file_size)
    return payload, extension.decode("ascii")

def decode_file(image_path, output_file=None):
    payload, extension = extract_hidden_file(image_path)
    if output_file is None:
        output_file = f"decoded_secret{extension}"
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(f"[SUCCESS] Hidden file extracted from: {image_path}")
    print(f"[OK] Saved to: {output}")
    if extension.lower() == ".txt":
        try:
            print("Message:")
            print(payload.decode("utf-8"))
        except UnicodeDecodeError:
            print("[NOTE] The extracted .txt file is not valid UTF-8; bytes were saved unchanged.")
    return output

def do_decoding(stego_image_fname, output_fname=None):
    try:
        decode_file(stego_image_fname, output_fname)
        return Status.e_success
    except (OSError, ValueError, struct.error, SteganoError) as exc:
        print(f"[ERROR] Decoding failed: {exc}")
        return Status.e_failure
