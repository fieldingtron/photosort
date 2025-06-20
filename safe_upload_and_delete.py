#!/usr/bin/env python3
"""
Safe Batch Upload and Delete Script for Immich (Python version)
Uploads files in batches, verifies upload, and only then deletes the local originals.

Requirements:
- immich CLI

Usage:
    python safe_upload_and_delete.py --album "Photo Export 2025" --batch-size 1000
"""
import os
import subprocess
import time
import argparse
from pathlib import Path

def find_files(extensions):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])

def get_server_count():
    try:
        result = subprocess.run(['immich', 'server-info'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'Total:' in line:
                return int(line.split()[-1])
    except Exception:
        return 0
    return 0

def main():
    parser = argparse.ArgumentParser(description="Safe batch upload and delete for Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=1000, help="Batch size")
    parser.add_argument('--log', default="safe_upload.log", help="Log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4'}
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

        logprint(f"🚀 Starting Safe Batch Upload with Verification at {time.ctime()}")
        logprint(f"Album: {args.album}")
        logprint(f"Batch size: {args.batch_size} files per batch")
        logprint(f"Process: Upload → Verify → Delete")
        logprint(f"===========================================")
        logprint(f"Total files to process: {total_files}")

        for i in range(0, total_files, args.batch_size):
            batch = files[i:i+args.batch_size]
            logprint(f"\n📤 Uploading batch {batch_num} ({len(batch)} files)...")
            before_count = get_server_count()
            try:
                result = subprocess.run([
                    'immich', 'upload', *batch,
                    '--album-name', args.album,
                    '--concurrency', str(args.concurrency)
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    # Wait for server to process
                    time.sleep(5)
                    after_count = get_server_count()
                    uploaded_count = after_count - before_count
                    if uploaded_count >= len(batch):
                        uploaded += len(batch)
                        logprint(f"✅ Batch {batch_num} uploaded and verified ({len(batch)} files)")
                        # Delete files after verification
                        for f in batch:
                            try:
                                os.remove(f)
                                deleted += 1
                            except Exception as e:
                                logprint(f"Failed to delete {f}: {e}")
                    else:
                        logprint(f"❌ Batch {batch_num} upload verification failed: {uploaded_count} new files detected, expected {len(batch)}")
                else:
                    logprint(f"❌ Batch {batch_num} failed: {result.stderr}")
            except Exception as e:
                logprint(f"❌ Batch {batch_num} failed: {e}")
            batch_num += 1
            time.sleep(args.delay)

        logprint(f"\n🎉 Upload completed!")
        logprint(f"Files uploaded and verified: {uploaded} / {total_files}")
        logprint(f"Files deleted: {deleted}")
        logprint(f"{time.ctime()}: Upload finished")

if __name__ == "__main__":
    main()
