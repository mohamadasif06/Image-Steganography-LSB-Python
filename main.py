"""Entry point for the Image Steganography project."""
from stegano.cli import main

if __name__ == "__main__":
    raise SystemExit(main())


"""py main.py -e my_source.bmp secret.txt 
   py main.py -s reference_images recovered_messages"""
