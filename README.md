# Complete Image Steganography Project (Python)

This is a Python conversion of the structure and intended workflow in the uploaded C project (`main.c`, `encode.c`, `encode.h`, `common.h`, and `types.h`). It preserves the original `#*` magic marker and the C-style metadata order.

## Project structure

```text
Image_Steganography_Python_Complete/
├── main.py
├── requirements.txt
├── secret.txt
├── reference_images/       # 30 supplied BMP images; encoded output is saved here
├── recovered_messages/     # extracted messages appear here
└── stegano/
    ├── __init__.py
    ├── common.py            # MAGIC_STRING = b"#*"
    ├── types.py             # Python equivalents of Status, OperationType, EncodeInfo
    ├── encode.py            # encoding and capacity functions
    ├── decode.py            # decoding functions
    ├── scan.py              # scans every BMP in a folder
    └── cli.py               # command-line interface
```

## 1. Run in VS Code (Windows)

1. Extract this ZIP file.
2. Open the `Image_Steganography_Python_Complete` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. No third-party package is needed; the project uses only the Python standard library. Check Python with:

```powershell
py --version
```

## 2. Write the secret message

Edit `secret.txt`, write the message you want to hide, and save it.

## 3. Encode: provide a source image file directly; encoded copy goes to `reference_images`

You do **not** need to create a `source_images` folder. Put the source BMP file anywhere convenient, such as the project root, or pass its full path from another folder. The source image is not moved or modified.

If `my_source.bmp` is in the project root, run:

```powershell
py main.py -e my_source.bmp secret.txt
```

By default, this creates `reference_images\my_source_stego.bmp`. Only the new encoded copy is saved in `reference_images`.

You can also provide a full path directly, without creating a folder in the project:

```powershell
py main.py -e "C:\Users\YourName\Pictures\source.bmp" secret.txt
```

An optional third argument lets you choose a different output path:

```powershell
py main.py -e my_source.bmp secret.txt reference_images\my_encoded_image.bmp
```

## 4. Retrieve: scan every image in `reference_images`

```powershell
py main.py -s reference_images recovered_messages
```

The scanner checks all BMP files in `reference_images`, including the encoded image, for the original `#*` marker. When it finds a valid marker and metadata, it extracts the hidden file into `recovered_messages`. Ordinary images without the marker are skipped. The scan does not rely on a particular image filename.

To extract from a known image directly (optional):

```powershell
py main.py -d reference_images\cover_01_stego.bmp recovered_message.txt
```

## Important compatibility notes

- The original C `common.h` defines `MAGIC_STRING` as `"#*"`; this project uses that same marker.
- The intended C metadata layout is retained: marker → 32-bit extension length → extension → 32-bit secret-file size → secret bytes. The supplied C implementation is a starter file with several functions left unfinished, so compatibility is with this intended layout, not a guarantee against every possible variation in a separately completed C program.
- This method hides data but does **not encrypt** it. Anyone who knows the format can extract it.
- Use uncompressed 24-bit BMP images. Do not resize, edit, or recompress the encoded image.
- The scanner examines BMP files recursively and saves each valid recovered file to the chosen output folder.
