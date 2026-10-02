"""Inspect DDS GPU readbacks or a raw BC1/BC7 image; no game assets belong in Git."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--raw-format", choices=("bc1", "bc7"))
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    data = args.input.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if args.raw_format:
        width, height = args.width, args.height
        if not width or not height or not (1 <= width <= 8192 and 1 <= height <= 8192):
            parser.error("Raw blocks require --width and --height between 1 and 8192")
        block_bytes = 8 if args.raw_format == "bc1" else 16
        required = ((width + 3) // 4) * ((height + 3) // 4) * block_bytes
        if len(data) < required:
            parser.error("Raw input is smaller than the first mip")
        header = struct.pack("<7I", 124, 0x81007, height, width, required, 0, 1)
        header += bytes(44) + struct.pack("<8I", 32, 4, 0x30315844, 0, 0, 0, 0, 0)
        header += struct.pack("<5I", 0x1000, 0, 0, 0, 0)
        dxgi = 71 if args.raw_format == "bc1" else 98
        data = b"DDS " + header + struct.pack("<5I", dxgi, 3, 0, 1, 0) + data[:required]
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        rgb = image.convert("RGB")
        lit_pixels = sum(1 for pixel in rgb.get_flattened_data() if any(pixel))
        result = {"sha256": digest, "size": list(image.size), "mode": image.mode,
                  "extrema": image.getextrema(), "nonzero_rgb_pixels": lit_pixels,
                  "total_pixels": image.width * image.height}
        if args.preview:
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            # Packed alpha is material data, not display opacity.
            rgb.save(args.preview)
        print(json.dumps(result))


if __name__ == "__main__":
    main()

