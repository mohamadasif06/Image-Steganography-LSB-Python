"""Encoding functions modeled on the supplied encode.c / encode.h structure.

Data format (each bit is stored in the LSB of one BMP pixel-data byte):
    MAGIC_STRING (#*) | 32-bit extension length | extension bytes |
    32-bit secret-file length | secret-file bytes

The metadata order and #* marker follow the supplied C starter project.
"""
from pathlib import Path
import struct
from .common import MAGIC_STRING, BMP_HEADER_MIN_SIZE
from .types import EncodeInfo, Status

_U32 = struct.Struct(">I")

class SteganoError(Exception):
    """Raised for invalid inputs, unsupported BMPs, or capacity errors."""

def _read_bmp(path):
    path = Path(path)
    if not path.is_file():
        raise SteganoError(f"File not found: {path}")
    data = path.read_bytes()
    if len(data) < BMP_HEADER_MIN_SIZE or data[:2] != b"BM":
        raise SteganoError(f"Not a valid BMP image: {path}")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40 or pixel_offset < BMP_HEADER_MIN_SIZE or pixel_offset > len(data):
        raise SteganoError("Unsupported BMP header or invalid pixel-data offset.")
    width, height = struct.unpack_from("<ii", data, 18)
    planes, bits_per_pixel = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    if width <= 0 or height == 0 or planes != 1 or bits_per_pixel != 24 or compression != 0:
        raise SteganoError("Use an uncompressed 24-bit RGB BMP image.")
    row_stride = ((width * 3 + 3) // 4) * 4
    pixel_bytes = row_stride * abs(height)
    if pixel_offset + pixel_bytes > len(data):
        raise SteganoError("BMP pixel data is truncated.")
    return data, pixel_offset, pixel_bytes

def get_image_size_for_bmp(image_path):
    """Return the number of image-data bytes available as LSB carriers."""
    _, _, pixel_bytes = _read_bmp(image_path)
    return pixel_bytes

def get_file_size(file_path):
    """Return secret file size in bytes."""
    return Path(file_path).stat().st_size

def encode_byte_to_lsb(data_byte, image_buffer):
    """Encode one byte into the LSBs of an 8-byte mutable buffer."""
    if len(image_buffer) < 8:
        raise SteganoError("An 8-byte carrier buffer is required.")
    value = data_byte if isinstance(data_byte, int) else ord(data_byte)
    for bit_index in range(8):
        bit = (value >> (7 - bit_index)) & 1
        image_buffer[bit_index] = (image_buffer[bit_index] & 0xFE) | bit
    return Status.e_success

def encode_size_to_lsb(size, image_buffer):
    """Encode an unsigned 32-bit integer into 32 carrier-byte LSBs."""
    if not 0 <= int(size) <= 0xFFFFFFFF:
        raise SteganoError("File size/metadata exceeds the 32-bit format limit.")
    if len(image_buffer) < 32:
        raise SteganoError("A 32-byte carrier buffer is required.")
    raw = _U32.pack(int(size))
    for byte_index, byte in enumerate(raw):
        start = byte_index * 8
        for bit_index in range(8):
            bit = (byte >> (7 - bit_index)) & 1
            pos = start + bit_index
            image_buffer[pos] = (image_buffer[pos] & 0xFE) | bit
    return Status.e_success

def _embed_bytes(carriers, offset, data):
    needed = len(data) * 8
    if offset + needed > len(carriers):
        raise SteganoError("Not enough BMP image capacity for the secret data.")
    for byte_index, value in enumerate(data):
        start = offset + byte_index * 8
        # A slice copy would not mutate the original bytearray, so use indices here.
        for bit_index in range(8):
            bit = (value >> (7 - bit_index)) & 1
            pos = start + bit_index
            carriers[pos] = (carriers[pos] & 0xFE) | bit
    return offset + needed

def _make_packet(secret_bytes, extension):
    ext_bytes = extension.encode("ascii")
    if not ext_bytes or len(ext_bytes) > 16:
        raise SteganoError("Secret file extension must be between 1 and 16 ASCII characters.")
    if len(secret_bytes) > 0xFFFFFFFF:
        raise SteganoError("Secret file is too large for this C-compatible 32-bit format.")
    return MAGIC_STRING + _U32.pack(len(ext_bytes)) + ext_bytes + _U32.pack(len(secret_bytes)) + secret_bytes

def read_and_validate_encode_args(argv, encInfo):
    """Validate C-style args: argv[2]=BMP, argv[3]=secret, argv[4]=optional BMP."""
    try:
        if len(argv) < 4:
            raise SteganoError("Usage: python main.py -e cover.bmp secret.txt [stego.bmp]")
        source = Path(argv[2])
        secret = Path(argv[3])
        # By default, the source image can be anywhere, but the encoded image
        # is saved into the project's reference_images folder.
        project_root = Path(__file__).resolve().parent.parent
        output = Path(argv[4]) if len(argv) > 4 else project_root / "reference_images" / f"{source.stem}_stego.bmp"
        if source.suffix.lower() != ".bmp":
            raise SteganoError("Cover image must have a .bmp extension.")
        if output.suffix.lower() != ".bmp":
            raise SteganoError("Output image must have a .bmp extension.")
        if not source.is_file():
            raise SteganoError(f"Cover image not found: {source}")
        if not secret.is_file():
            raise SteganoError(f"Secret file not found: {secret}")
        if source.resolve() == output.resolve():
            raise SteganoError("Output image must differ from the original cover image.")
        encInfo.src_image_fname = str(source)
        encInfo.secret_fname = str(secret)
        encInfo.stego_image_fname = str(output)
        encInfo.extn_secret_file = secret.suffix or ".bin"
        encInfo.size_secret_file = get_file_size(secret)
        encInfo.image_capacity = get_image_size_for_bmp(source)
        return Status.e_success
    except (OSError, ValueError, IndexError, SteganoError) as exc:
        print(f"[ERROR] {exc}")
        return Status.e_failure

def open_files(encInfo):
    """Compatibility helper: verify all paths are readable/writable."""
    try:
        for path in (encInfo.src_image_fname, encInfo.secret_fname):
            if not Path(path).is_file():
                raise SteganoError(f"Input file not found: {path}")
        Path(encInfo.stego_image_fname).parent.mkdir(parents=True, exist_ok=True)
        return Status.e_success
    except (OSError, SteganoError) as exc:
        print(f"[ERROR] {exc}")
        return Status.e_failure

def check_capacity(encInfo):
    try:
        ext = encInfo.extn_secret_file.encode("ascii")
        needed_bytes = len(MAGIC_STRING) + 4 + len(ext) + 4 + encInfo.size_secret_file
        if needed_bytes * 8 > encInfo.image_capacity:
            raise SteganoError(
                f"Image capacity is too small. Need {needed_bytes} carrier bytes; "
                f"available: {encInfo.image_capacity // 8} payload bytes."
            )
        return Status.e_success
    except (UnicodeEncodeError, SteganoError) as exc:
        print(f"[ERROR] {exc}")
        return Status.e_failure

def copy_bmp_header(fptr_src_image, fptr_dest_image):
    """Copy bytes before the pixel data (works with standard 24-bit BMP headers)."""
    source = fptr_src_image.read()
    if len(source) < BMP_HEADER_MIN_SIZE or source[:2] != b"BM":
        return Status.e_failure
    offset = struct.unpack_from("<I", source, 10)[0]
    fptr_dest_image.write(source[:offset])
    return Status.e_success

def encode_magic_string(magic_string, encInfo):
    # Encoding is performed in do_encoding so metadata remains in one ordered packet.
    try:
        value = magic_string.encode("ascii") if isinstance(magic_string, str) else bytes(magic_string)
        return Status.e_success if value == MAGIC_STRING else Status.e_failure
    except (UnicodeEncodeError, TypeError, ValueError):
        return Status.e_failure

def encode_secret_file_extn_size(size, encInfo):
    return Status.e_success if 0 <= int(size) <= 0xFFFFFFFF else Status.e_failure

def encode_secret_file_extn(file_extn, encInfo):
    return Status.e_success if file_extn else Status.e_failure

def encode_secret_file_size(file_size, encInfo):
    return Status.e_success if 0 <= int(file_size) <= 0xFFFFFFFF else Status.e_failure

def encode_secret_file_data(encInfo):
    return Status.e_success if Path(encInfo.secret_fname).is_file() else Status.e_failure

def copy_remaining_img_data(fptr_src, fptr_dest):
    fptr_dest.write(fptr_src.read())
    return Status.e_success

def do_encoding(encInfo):
    """Run the full encoding workflow and write a BMP output."""
    if open_files(encInfo) is not Status.e_success:
        return Status.e_failure
    try:
        source_data, pixel_offset, pixel_size = _read_bmp(encInfo.src_image_fname)
        secret_data = Path(encInfo.secret_fname).read_bytes()
        extension = Path(encInfo.secret_fname).suffix or ".bin"
        packet = _make_packet(secret_data, extension)
        if len(packet) * 8 > pixel_size:
            max_payload = max(0, pixel_size // 8 - len(MAGIC_STRING) - 8 - len(extension))
            raise SteganoError(
                f"Secret file does not fit in this image. Approximate maximum secret size: {max_payload} bytes."
            )
        encoded = bytearray(source_data)
        carriers = bytearray(encoded[pixel_offset:pixel_offset + pixel_size])
        _embed_bytes(carriers, 0, packet)
        encoded[pixel_offset:pixel_offset + pixel_size] = carriers
        output = Path(encInfo.stego_image_fname)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
        print("[OK] Source BMP opened.")
        print(f"[OK] Image capacity: {pixel_size} carrier bytes.")
        print(f"[OK] Secret file size: {len(secret_data)} bytes.")
        print(f"[OK] Magic marker '{MAGIC_STRING.decode()}' embedded.")
        print(f"[SUCCESS] Encoded image saved to: {output}")
        return Status.e_success
    except (OSError, ValueError, struct.error, SteganoError) as exc:
        print(f"[ERROR] Encoding failed: {exc}")
        return Status.e_failure

def encode_file(cover_image, secret_file, output_image=None):
    cover_path = Path(cover_image)
    # The user supplies a separate source image. Save the encoded copy into
    # the project's reference_images folder by default, leaving the source intact.
    if output_image is None:
        project_root = Path(__file__).resolve().parent.parent
        output_image = project_root / "reference_images" / f"{cover_path.stem}_stego.bmp"
    output_image = Path(output_image)
    info = EncodeInfo(str(cover_path), str(secret_file), str(output_image))
    info.extn_secret_file = Path(secret_file).suffix or ".bin"
    try:
        info.size_secret_file = get_file_size(secret_file)
        info.image_capacity = get_image_size_for_bmp(cover_image)
    except (OSError, SteganoError) as exc:
        raise SteganoError(str(exc)) from exc
    if check_capacity(info) is not Status.e_success:
        raise SteganoError("Capacity check failed.")
    if do_encoding(info) is not Status.e_success:
        raise SteganoError("Encoding failed; see the error above.")
    return Path(output_image)
