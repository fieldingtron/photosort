#!/usr/bin/env python3
"""
Simple and Reliable Batch Upload Script for Immich (Python version)
Uploads files in batches, verifies, and deletes after upload.

Usage:
    python simple_batch_upload.py --album "Photo Export 2025" --batch-size 100
"""
import os
import subprocess
import time
import argparse
from pathlib import Path

def find_files(extensions):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])

def main():
    parser = argparse.ArgumentParser(description="Batch upload, verify, and delete files for Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=100, help="Batch size")
    parser.add_argument('--log', default="batch_upload.log", help="Log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.mov', '.mp4', '.avi', '.gif'}
    files = find_files(EXTENSIONS)
    total_files = len(files)
    uploaded = 0
    deleted = 0
    batch_num = 1

    with open(args.log, 'w') as log:
        def logprint(msg):
            print(msg)
            print(msg, file=log)
            log.flush()

        logprint(f"\U0001F680 Batch Upload and Delete Script - {time.ctime()}")
        logprint(f"Album: {args.album}")
        logprint(f"Batch size: {args.batch_size} files")
        logprint(f"Total files to process: {total_files}")

        for i in range(0, total_files, args.batch_size):
            batch = files[i:i+args.batch_size]
            logprint(f"\n\U0001F4E4 Processing Batch {batch_num} ({len(batch)} files)...")
            try:
                result = subprocess.run([
                    'immich', 'upload', *batch,
                    '--album-name', args.album,
                    '--concurrency', str(args.concurrency)
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    uploaded += len(batch)
                    logprint(f"\u2705 Batch {batch_num} completed ({len(batch)} files)")
                    # Delete files after upload
                    for f in batch:
                        try:
                            os.remove(f)
                            deleted += 1
                        except Exception as e:
                            logprint(f"Failed to delete {f}: {e}")
                else:
                    logprint(f"\u274C Batch {batch_num} failed: {result.stderr}")
            except Exception as e:
                logprint(f"\u274C Batch {batch_num} failed: {e}")
            batch_num += 1
            time.sleep(args.delay)

        logprint(f"\n\U0001F389 Upload completed!")
        logprint(f"Files uploaded: {uploaded} / {total_files}")
        logprint(f"Files deleted: {deleted}")
        logprint(f"{time.ctime()}: Upload finished")

if __name__ == "__main__":
    main()
