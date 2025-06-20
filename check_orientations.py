#!/usr/bin/env python3
"""
Check EXIF orientation of the first 10 images in the current directory (Python version).

Usage:
    python check_orientations.py
"""
import os
from pathlib import Path
from PIL import Image
import piexif

def get_orientation(file):
    try:
        img = Image.open(file)
        exif = img._getexif()
        if exif is not None:
            orientation = exif.get(274, 1)  # 274 is the EXIF tag for Orientation
        else:
            orientation = 1
    except Exception:
        orientation = 1
    return orientation

def orientation_description(orientation):
    return {
        1: "None (Normal)",
        2: "Flip horizontal",
        3: "Rotate 180°",
        4: "Flip vertical",
        5: "Rotate 90° CCW + flip",
        6: "Rotate 90° CW",
        7: "Rotate 90° CW + flip",
        8: "Rotate 90° CCW"
    }.get(orientation, f"Unknown ({orientation})")

def main():
    print("🔍 Checking EXIF orientation of first 10 images...")
    print("===========================================")
    count = 0
    for file in sorted(Path('.').iterdir()):
        if file.is_file() and file.suffix.lower() in {'.jpg', '.jpeg', '.heic'}:
            if count < 10:
                orientation = get_orientation(file)
                desc = orientation_description(orientation)
                print(f"{file}: Orientation {orientation} - {desc}")
                count += 1
    print("\nReady to run: rotate_and_upload.py (Python equivalent)")

if __name__ == "__main__":
    main()
