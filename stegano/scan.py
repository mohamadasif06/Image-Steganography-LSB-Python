"""Find a hidden payload by checking the #* marker across BMP images."""
from pathlib import Path
from .common import SUPPORTED_IMAGE_EXTENSIONS
from .decode import extract_hidden_file
from .encode import SteganoError

def scan_folder(image_folder, output_folder):
    folder = Path(image_folder)
    if not folder.is_dir():
        raise SteganoError(f"Image folder not found: {folder}")
    images = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS)
    if not images:
        print(f"No BMP images found in: {folder}")
        return 0
    print(f"Scanning {len(images)} BMP image(s) for marker '#*'...")
    output_dir = Path(output_folder)
    found = 0
    for image in images:
        try:
            payload, extension = extract_hidden_file(image)
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / f"{image.stem}_recovered{extension}"
            index = 1
            while target.exists():
                target = output_dir / f"{image.stem}_recovered_{index}{extension}"
                index += 1
            target.write_bytes(payload)
            found += 1
            print(f"[FOUND] {image} -> {target} ({len(payload)} bytes)")
            if extension.lower() == ".txt":
                try:
                    print("        Message:", payload.decode("utf-8"))
                except UnicodeDecodeError:
                    print("        Text payload is not UTF-8; saved raw bytes.")
        except SteganoError as exc:
            print(f"[skip] {image.name}: {exc}")
    print(f"Scan complete. Found {found} image(s) containing valid hidden data.")
    return found
