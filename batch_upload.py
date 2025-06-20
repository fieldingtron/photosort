#!/usr/bin/env python3
"""
Batch upload script for Immich (Python version)
Uploads files in batches to avoid overwhelming the system.

Usage:
    python batch_upload.py --album "Photo Export 2025" --batch-size 100 --log upload_log.txt
"""
import os
import subprocess
import time
import argparse
from pathlib import Path

def find_files(extensions):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])

def main():
    parser = argparse.ArgumentParser(description="Batch upload files to Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=100, help="Batch size")
    parser.add_argument('--log', default="upload_log.txt", help="Log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4'}
    files = find_files(EXTENSIONS)
    total_files = len(files)
    uploaded = 0
    batch_num = 1

    with open(args.log, 'w') as log:
        def logprint(msg):
            print(msg)
            print(msg, file=log)
            log.flush()

        logprint(f"🚀 Starting batch upload to Immich...")
        logprint(f"Album: {args.album}")
        logprint(f"Batch size: {args.batch_size} files")
        logprint(f"{time.ctime()}: Starting upload")
        logprint(f"Total files to upload: {total_files}")

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
