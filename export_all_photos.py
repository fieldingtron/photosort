#!/usr/bin/env python3
"""
Export all photos from the macOS Photos library using osxphotos.
Exports original files to a specified directory, placing all files directly in the output folder.
Removes duplicates by exporting only one copy per unique photo (by file hash).

Requirements:
- osxphotos (pip install osxphotos)

Usage:
    python export_all_photos.py --output /path/to/export_dir [--limit 10]
"""

import os
import argparse
import sys
from pathlib import Path
import hashlib
import pickle

try:
    import osxphotos
except ImportError:
    print("osxphotos is not installed. Please run: pip install osxphotos")
    sys.exit(1)

def get_file_hash(filepath, block_size=65536):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def export_photos(output_dir, limit=None):
    keep_cache_path = Path(output_dir) / '.keep_cache.pkl'
    if keep_cache_path.exists():
        with open(keep_cache_path, 'rb') as f:
            keep_cache = pickle.load(f)
    else:
        keep_cache = set()

    photosdb = osxphotos.PhotosDB()
    photos = photosdb.photos()
    print(f"Found {len(photos)} photos in the Photos library.")

    if limit is not None:
        photos = photos[:limit]
        print(f"Limiting export to first {limit} photos.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes = set()
    exported_count = 0
    for photo in photos:
        # Skip if already marked as keep
        if photo.uuid in keep_cache:
            continue
        temp_filename = f"temp_{photo.uuid}{Path(photo.original_filename).suffix}"
        exported = photo.export(
            output_dir,
            overwrite=True,
            use_photos_export=False,
            exiftool=True,
            filename=temp_filename
        )
        if exported:
            temp_path = output_dir / temp_filename
            file_hash = get_file_hash(temp_path)
            if file_hash in seen_hashes:
                print(f"Duplicate detected (hash): {temp_path}, removing.")
                temp_path.unlink()  # Remove duplicate
                continue
            seen_hashes.add(file_hash)
            # Rename temp file to final name
            final_filename = f"{photo.uuid}{Path(photo.original_filename).suffix}"
            final_path = output_dir / final_filename
            temp_path.rename(final_path)
            print(f"Exported: {final_path}")
            exported_count += 1
            # Mark as kept
            keep_cache.add(photo.uuid)
            with open(keep_cache_path, 'wb') as f:
                pickle.dump(keep_cache, f)
        else:
            print(f"Skipped or failed: {photo.original_filename}")
    print(f"Total unique files exported: {exported_count}")

def main():
    parser = argparse.ArgumentParser(description="Export all photos from macOS Photos using osxphotos.")
    parser.add_argument("--output", "-o", required=True, help="Directory to export photos to.")
    parser.add_argument("--limit", "-l", type=int, help="Limit the number of photos to export (for testing)")
    args = parser.parse_args()
    export_photos(args.output, args.limit)

if __name__ == "__main__":
    main()
