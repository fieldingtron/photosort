#!/usr/bin/env python3
"""
Test version - Safe Batch Upload and Delete Script for Immich (Python version)
Processes only 10 files in batches of 5 for testing.

Usage:
    python test_upload.py --album "Photo Export 2025" --batch-size 5 --max-files 10
"""
import os
import subprocess
import time
import argparse
from pathlib import Path

def find_files(extensions, max_files):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])[:max_files]

def main():
    parser = argparse.ArgumentParser(description="Test safe batch upload and delete for Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=5, help="Batch size")
    parser.add_argument('--max-files', type=int, default=10, help="Max files to process")
    parser.add_argument('--log', default="test_upload.log", help="Log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}
    files = find_files(EXTENSIONS, args.max_files)
    total_files = len(files)
    uploaded = 0
    deleted = 0
    batch_num = 1

    with open(args.log, 'w') as log:
        def logprint(msg):
            print(msg)
            print(msg, file=log)
            log.flush()

        logprint(f"🧪 TEST MODE: Safe Batch Upload with Verification")
        logprint(f"Will process only first {args.max_files} files in batches of {args.batch_size}")
        logprint(f"Album: {args.album}")
        logprint(f"Found {total_files} files for testing")
        if total_files == 0:
            logprint("❌ No files found for testing")
            return
        logprint(f"⚠️  This will DELETE these {total_files} local files after successful upload!")
        # No prompt for automation, but you can add input() if desired
        for i in range(0, total_files, args.batch_size):
            batch = files[i:i+args.batch_size]
            logprint(f"\n📤 Testing batch: {len(batch)} files...")
            try:
                result = subprocess.run([
                    'immich', 'upload', *batch,
                    '--album-name', args.album,
                    '--concurrency', str(args.concurrency)
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    uploaded += len(batch)
                    logprint(f"✅ Batch {batch_num} completed ({len(batch)} files)")
                    for f in batch:
                        try:
                            os.remove(f)
                            deleted += 1
                        except Exception as e:
                            logprint(f"Failed to delete {f}: {e}")
                else:
                    logprint(f"❌ Batch {batch_num} failed: {result.stderr}")
            except Exception as e:
                logprint(f"❌ Batch {batch_num} failed: {e}")
            batch_num += 1
            time.sleep(args.delay)
        logprint(f"\n✅ No more files")
        logprint(f"Files uploaded: {uploaded} / {total_files}")
        logprint(f"Files deleted: {deleted}")
        logprint(f"{time.ctime()}: Test finished")

if __name__ == "__main__":
    main()
