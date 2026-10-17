"""Command-line interface. Supports the original C-style -e/-d plus -s scanning."""
import argparse
import sys
from .encode import encode_file, SteganoError
from .decode import decode_file
from .scan import scan_folder

def _parser():
    parser = argparse.ArgumentParser(
        description="BMP image steganography: hide a file, extract it, or scan a folder of images.",
        epilog=("Examples: python main.py -e reference_images/cover_01.bmp secret.txt | "
                "python main.py -d stego.bmp recovered.txt | "
                "python main.py -s reference_images recovered_messages")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    enc = sub.add_parser("encode", aliases=["-e"], help="Hide a file in a BMP image")
    enc.add_argument("cover_image")
    enc.add_argument("secret_file")
    enc.add_argument("output_image", nargs="?", default=None,
                     help="Optional output path; by default, saves <cover>_stego.bmp beside the cover image")
    dec = sub.add_parser("decode", aliases=["-d"], help="Extract hidden file from one BMP")
    dec.add_argument("stego_image")
    dec.add_argument("output_file", nargs="?", default=None)
    scan = sub.add_parser("scan", aliases=["-s"], help="Scan a folder for an image containing the marker")
    scan.add_argument("image_folder")
    scan.add_argument("output_folder", nargs="?", default="recovered_messages")
    return parser

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # Keep the exact original C-style flags easy to use in a terminal.
    if argv and argv[0] in ("-e", "-d", "-s"):
        argv = [{"-e": "encode", "-d": "decode", "-s": "scan"}[argv[0]]] + argv[1:]
    args = _parser().parse_args(argv)
    try:
        if args.command in ("encode", "-e"):
            encode_file(args.cover_image, args.secret_file, args.output_image)
        elif args.command in ("decode", "-d"):
            decode_file(args.stego_image, args.output_file)
        elif args.command in ("scan", "-s"):
            scan_folder(args.image_folder, args.output_folder)
        return 0
    except (OSError, ValueError, SteganoError) as exc:
        print(f"[ERROR] {exc}")
        return 2
