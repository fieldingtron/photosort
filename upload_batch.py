#!/usr/bin/env python3
"""
Robust batch upload script for Immich (Python version)
Uploads files in batches, logs progress, and handles errors.

Usage:
    python upload_batch.py --album "Photo Export 2025" --batch-size 50
"""
import os
import subprocess
import time
import argparse
from pathlib import Path

def find_files(extensions, max_files=1000):
    return sorted([str(p) for p in Path('.').iterdir() if p.is_file() and p.suffix.lower() in extensions])[:max_files]

def main():
    parser = argparse.ArgumentParser(description="Robust batch upload files to Immich.")
    parser.add_argument('--album', default="Photo Export 2025", help="Album name")
    parser.add_argument('--batch-size', type=int, default=50, help="Batch size")
    parser.add_argument('--log', default="upload_progress.log", help="Log file")
    parser.add_argument('--success-log', default="uploaded_files.log", help="Success log file")
    parser.add_argument('--error-log', default="upload_errors.log", help="Error log file")
    parser.add_argument('--concurrency', type=int, default=2, help="Immich upload concurrency")
    parser.add_argument('--delay', type=int, default=2, help="Delay (seconds) between batches")
    args = parser.parse_args()

    EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4'}
    files = find_files(EXTENSIONS)
    total_files = len(files)
    uploaded = 0
    failed = 0
    batch_num = 1

    with open(args.log, 'w') as log, open(args.success_log, 'w') as slog, open(args.error_log, 'w') as elog:
        def logprint(msg):
            print(msg)
            print(msg, file=log)
            log.flush()
        def slogprint(msg):
            print(msg, file=slog)
            slog.flush()
        def elogprint(msg):
            print(msg, file=elog)
            elog.flush()

        logprint(f"\U0001F680 Starting Immich batch upload at {time.ctime()}")
        logprint(f"Album: {args.album}")
        logprint(f"Batch size: {args.batch_size} files per batch")
        logprint(f"Found {total_files} files to upload")

        if total_files == 0:
            logprint("\u274C No files found to upload")
            return

        for i in range(0, total_files, args.batch_size):
            batch = files[i:i+args.batch_size]
            logprint(f"\U0001F4E4 Batch {batch_num}: Uploading {len(batch)} files...")
            try:
                result = subprocess.run([
                    'immich', 'upload', *batch,
                    '--album-name', args.album,
                    '--concurrency', str(args.concurrency)
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    uploaded += len(batch)
                    logprint(f"\u2705 Batch {batch_num}: Successfully uploaded {len(batch)} files")
                    for f in batch:
                        slogprint(f)
                else:
                    failed += len(batch)
                    logprint(f"\u274C Batch {batch_num}: Failed to upload {len(batch)} files")
                    elogprint(result.stderr)
            except Exception as e:
                failed += len(batch)
                logprint(f"\u274C Batch {batch_num}: Failed to upload {len(batch)} files: {e}")
                elogprint(str(e))
            batch_num += 1
            time.sleep(args.delay)

        logprint(f"\n\U0001F389 Upload completed!")
        logprint(f"Files uploaded: {uploaded} / {total_files}")
        logprint(f"Files failed: {failed}")
        logprint(f"{time.ctime()}: Upload finished")

if __name__ == "__main__":
    main()
