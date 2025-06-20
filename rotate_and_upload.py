#!/usr/bin/env python3
"""
Auto-rotate images based on EXIF data, then upload in batches to Immich (Python version).

Requirements:
- Pillow
- piexif
- immich CLI

Usage:
    python rotate_and_upload.py --album "Photo Export 2025" --batch-size 100
"""
import os
import subprocess
import time
import argparse
from pathlib import Path
from PIL import Image, ImageOps
import piexif

def auto_rotate_image(file):
    try:
        img = Image.open(file)
        exif = img.info.get('exif', None)
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        img.save(file, exif=exif)
        return True
    except Exception as e:
        print(f"Failed to auto-rotate {file}: {e}")
        return False

def find_files(extensions):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])

def main():
    parser = argparse.ArgumentParser(description="Auto-rotate and batch upload files to Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=100, help="Batch size")
    parser.add_argument('--log', default="rotate_upload.log", help="Log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}
    files = find_files(EXTENSIONS)
    total_files = len(files)
    rotated = 0
    uploaded = 0
    batch_num = 1

    with open(args.log, 'w') as log:
        def logprint(msg):
            print(msg)
            print(msg, file=log)
            log.flush()

        logprint(f"🔄 Auto-Rotate and Upload Script Started at {time.ctime()}")
        logprint(f"Album: {args.album}")
        logprint(f"Batch size: {args.batch_size} files")
        logprint(f"Process: Rotate → Upload")
        logprint(f"===========================================")
        logprint(f"Total files to process: {total_files}")

        # Auto-rotate all images first
        for file in files:
            if auto_rotate_image(file):
                rotated += 1
        logprint(f"Auto-rotated {rotated} images.")

        # Upload in batches
        for i in range(0, total_files, args.batch_size):
            batch = files[i:i+args.batch_size]
            logprint(f"\n📤 Uploading batch {batch_num} ({len(batch)} files)...")
            try:
                result = subprocess.run([
                    'immich', 'upload', *batch,
                    '--album-name', args.album,
                    '--concurrency', str(args.concurrency)
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    uploaded += len(batch)
                    logprint(f"✅ Batch {batch_num} completed ({len(batch)} files)")
                else:
                    logprint(f"❌ Batch {batch_num} failed: {result.stderr}")
            except Exception as e:
                logprint(f"❌ Batch {batch_num} failed: {e}")
            batch_num += 1
            time.sleep(args.delay)

        logprint(f"\n🎉 Upload completed!")
        logprint(f"Files uploaded: {uploaded} / {total_files}")
        logprint(f"{time.ctime()}: Upload finished")

if __name__ == "__main__":
    main()
