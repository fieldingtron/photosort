import os
import shutil
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import json
import argparse
from tqdm import tqdm
from dotenv import load_dotenv

# CONFIGURABLE: Set the directory to crawl
load_dotenv()
SOURCE_DIR = os.getenv("SOURCE_DIR")
DEST_DIR = os.getenv("DEST_DIR")

# Supported image and video extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.3gp'}

HASH_DB_PATH = os.path.join(DEST_DIR, "file_hashes.json")

def get_file_year(filepath, is_image):
    if is_image:
        try:
            image = Image.open(filepath)
            exif_data = image._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == 'DateTimeOriginal':
                        return value[:4]  # 'YYYY:MM:DD ...'
        except Exception:
            pass
    # Fallback: use file's last modified year
    return str(datetime.fromtimestamp(os.path.getmtime(filepath)).year)

def file_hash(filepath):
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def load_hash_db():
    if os.path.exists(HASH_DB_PATH):
        try:
            with open(HASH_DB_PATH, 'r') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_hash_db(hash_set):
    try:
        with open(HASH_DB_PATH, 'w') as f:
            json.dump(list(hash_set), f)
    except Exception as e:
        print(f"Could not save hash db: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description="Sort and deduplicate photos and videos by year.")
    parser.add_argument('-H', '--rehash', action='store_true', help='Re-hash all files in the destination directory')
    parser.add_argument('--dups', action='store_true', help='Remove duplicates from the destination directory')
    return parser.parse_args()


def remove_dups_from_dest():
    print('Scanning for duplicates in destination...')
    hash_to_file = {}
    dups = []
    dest_files = []
    for root, _, files in os.walk(DEST_DIR):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                dest_files.append(os.path.join(root, name))
    for file_path in tqdm(dest_files, desc='Checking for duplicates in destination'):
        try:
            h = file_hash(file_path)
            if h in hash_to_file:
                dups.append(file_path)
            else:
                hash_to_file[h] = file_path
        except Exception:
            pass
    print(f"Found {len(dups)} duplicates in destination.")
    for dup in dups:
        try:
            os.remove(dup)
            print(f"Removed duplicate: {dup}")
        except Exception as e:
            print(f"Could not remove duplicate {dup}: {e}")
    print(f"Removed {len(dups)} duplicates from destination.")

def crawl_and_sort_media(rehash_dest=False):
    seen_hashes = load_hash_db() if not rehash_dest else set()
    # Hash all files already in DEST_DIR if rehash_dest is True
    if rehash_dest:
        dest_files = []
        for root, _, files in os.walk(DEST_DIR):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                    dest_files.append(os.path.join(root, name))
        for file_path in tqdm(dest_files, desc='Hashing destination files'):
            try:
                seen_hashes.add(file_hash(file_path))
            except Exception:
                pass
    # Process source files with progress bar
    source_files = []
    for root, _, files in os.walk(SOURCE_DIR):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext in IMAGE_EXTS or ext in VIDEO_EXTS:
                source_files.append((root, name))
    for root, name in tqdm(source_files, desc='Processing source files'):
        ext = os.path.splitext(name)[1].lower()
        is_image = ext in IMAGE_EXTS
        src_path = os.path.join(root, name)
        media_hash = file_hash(src_path)
        if media_hash in seen_hashes:
            print(f"Duplicate removed: {src_path}")
            os.remove(src_path)
            continue
        seen_hashes.add(media_hash)
        year = get_file_year(src_path, is_image)
        year_dir = os.path.join(DEST_DIR, year)
        os.makedirs(year_dir, exist_ok=True)
        dest_path = os.path.join(year_dir, name)
        # Avoid overwriting files with same name
        base, ext = os.path.splitext(name)
        count = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(year_dir, f"{base}_{count}{ext}")
            count += 1
        shutil.move(src_path, dest_path)
        print(f"Moved: {src_path} -> {dest_path}")
    save_hash_db(seen_hashes)
    # Remove .DS_Store, .picasa.ini, and Thumbs.db files and empty folders (ignoring these files)
    for dirpath, dirnames, filenames in os.walk(SOURCE_DIR, topdown=False):
        for special_file in ['.DS_Store', '.picasa.ini', 'Thumbs.db']:
            special_path = os.path.join(dirpath, special_file)
            if special_file in filenames:
                try:
                    os.remove(special_path)
                    print(f"Removed: {special_path}")
                except Exception as e:
                    print(f"Could not remove {special_path}: {e}")
        # Check if folder is empty or only contains .DS_Store/.picasa.ini/Thumbs.db
        remaining_files = [f for f in os.listdir(dirpath) if f not in ['.DS_Store', '.picasa.ini', 'Thumbs.db']]
        if not remaining_files and not dirnames:
            try:
                os.rmdir(dirpath)
                print(f"Removed empty folder: {dirpath}")
            except Exception as e:
                print(f"Could not remove {dirpath}: {e}")
    # Recursively remove empty folders in DEST_DIR, bottom-up
    for dirpath, dirnames, filenames in os.walk(DEST_DIR, topdown=False):
        # Only consider as empty if no files or folders remain
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                print(f"Removed empty folder: {dirpath}")
            except Exception as e:
                print(f"Could not remove {dirpath}: {e}")

if __name__ == "__main__":
    args = parse_args()
    if args.dups:
        remove_dups_from_dest()
    else:
        crawl_and_sort_media(rehash_dest=args.rehash)
    print("Done.")
