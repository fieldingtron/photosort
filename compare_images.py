"""
Interactive script to find, display, and manage visually similar images in a directory using perceptual hashing.

Features:
- Persistent hash cache for fast repeated runs.
- Persistent reviewed and deleted caches to avoid re-reviewing or re-deleting images.
- Skips macOS resource fork files (._).
- Progress bar for hashing step.
- Interactive GUI for each group of similar images:
    - Buttons below each image: "Keep", "Delete", "Delete All"
    - Clicking "Delete" deletes that image and moves to next group.
    - Clicking "Delete All" deletes all images in the group.
    - Clicking "Keep" keeps all images in the group and moves to next group.
    - Auto-advance after 5 seconds if no action is taken (defaults to "Keep").

Requirements:
- pillow
- pillow-heif
- matplotlib
- imagehash
- tqdm

Usage:
    python compare_images.py /path/to/image_directory [--hash phash|ahash|dhash|whash] [--threshold 5]
"""

import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be .* leaked semaphore objects")

import os
import time
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import imagehash
import argparse
import pickle
from tqdm import tqdm
import hashlib

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("Warning: pillow-heif not installed. HEIC images may not be supported.")

REVIEWED_CACHE = ".reviewed_groups.pkl"
DELETED_CACHE = ".deleted_images.pkl"

def compute_hash(image_path, hash_func):
    try:
        img = Image.open(image_path)
        if img.mode == 'P' and 'transparency' in img.info:
            img = img.convert('RGBA')
        return hash_func(img)
    except Exception as e:
        print(f"Error hashing {image_path}: {e}")
        return None

def load_pickle_cache(path):
    if Path(path).exists():
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return set()
    return set()

def save_pickle_cache(path, cache):
    with open(path, 'wb') as f:
        pickle.dump(cache, f)

def load_hash_cache(directory, hash_name):
    cache_path = Path(directory) / f'.hash_cache_{hash_name}.pkl'
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_hash_cache(directory, hash_name, cache):
    cache_path = Path(directory) / f'.hash_cache_{hash_name}.pkl'
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f)

def show_group_interactive(group, group_id, reviewed_cache, deleted_cache, auto=False):
    import matplotlib.widgets as mwidgets
    import numpy as np
    from matplotlib import pyplot as plt
    from PIL import Image, ExifTags
    import matplotlib
    import re
    n = len(group)
    # Helper to get resolution
    def get_resolution(img_path):
        try:
            with Image.open(img_path) as img:
                return img.width * img.height
        except Exception:
            return 0
    # Helper to get date from EXIF or filename
    def get_date(img_path):
        # Try EXIF first
        try:
            with Image.open(img_path) as img:
                exif = img._getexif()
                if exif:
                    for tag, value in exif.items():
                        decoded = ExifTags.TAGS.get(tag, tag)
                        if decoded in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
                            return value
        except Exception:
            pass
        # Fallback: look for November 2023 in filename
        fname = os.path.basename(img_path)
        # Match 2023-11-*, 202311*, 11-2023, 112023, etc.
        match = re.search(r'(2023[-]?11[-]?\d{2}|202311\d{2}|11[-]?2023|112023)', fname)
        if match:
            return '2023-11'
        return ''
    # Custom sort for 2-image groups
    if n == 2:
        res0 = get_resolution(group[0][0])
        res1 = get_resolution(group[1][0])
        date0 = get_date(group[0][0])
        date1 = get_date(group[1][0])
        is_nov2023_0 = ('2023-11' in date0 or '202311' in date0 or '11-2023' in date0 or '112023' in date0)
        is_nov2023_1 = ('2023-11' in date1 or '202311' in date1 or '11-2023' in date1 or '112023' in date1)
        # If one is Nov 2023 and is not higher quality, put it on the right
        if is_nov2023_0 and (res0 <= res1):
            group = [group[1], group[0]]
        elif is_nov2023_1 and (res1 <= res0):
            group = [group[0], group[1]]
        else:
            # Default: higher quality left
            group = sorted(group, key=lambda x: get_resolution(x[0]), reverse=True)
    else:
        # Default: sort by quality
        group = sorted(group, key=lambda x: get_resolution(x[0]), reverse=True)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 5), constrained_layout=True)
    if n == 1:
        axes = [axes]
    result = {'action': None, 'target': None}
    button_refs = []
    keep_callbacks = []
    action_taken = [False]  # Use list for mutability in closure
    def make_keep_callback(idx):
        def callback(event=None):
            if not action_taken[0]:
                result['action'] = 'keep_one'
                result['target'] = group[idx][0]
                action_taken[0] = True
                plt.close(fig)
        return callback
    def delete_all_callback(event=None):
        if not action_taken[0]:
            result['action'] = 'delete_all'
            action_taken[0] = True
            plt.close(fig)
    # Display images and keep buttons
    for i, (img_path, _) in enumerate(group):
        img = Image.open(img_path)
        if img.mode == 'P' and 'transparency' in img.info:
            img = img.convert('RGBA')
        axes[i].imshow(img)
        axes[i].set_title(os.path.basename(img_path), fontsize=10)
        axes[i].axis('off')
    # Place keep buttons below each image
    button_axes = []
    for i in range(n):
        left = 0.05 + i * (0.9 / n)
        width = 0.9 / n - 0.01
        ax_btn = plt.axes([left, 0.13, width, 0.07])
        btn = mwidgets.Button(ax_btn, 'Keep', color='green', hovercolor='lime')
        cb = make_keep_callback(i)
        btn.on_clicked(cb)
        button_refs.append(btn)
        keep_callbacks.append(cb)
        button_axes.append(ax_btn)
    # Place delete all button below all images
    ax_delall = plt.axes([0.4, 0.03, 0.2, 0.07])
    btn_delall = mwidgets.Button(ax_delall, 'Delete All', color='red', hovercolor='salmon')
    btn_delall.on_clicked(delete_all_callback)
    # Preselect the leftmost 'Keep' button and bind Return/Enter, Left, Right, Down to actions
    def on_key(event):
        if event.key in ('enter', 'return', 'left'):
            keep_callbacks[0]()
        elif event.key == 'right':
            keep_callbacks[-1]()
        elif event.key == 'down':
            delete_all_callback()
    fig.canvas.mpl_connect('key_press_event', on_key)
    # Auto-approve leftmost after 7 seconds if --auto is set, using matplotlib timer
    def auto_approve(event=None):
        if not action_taken[0]:
            keep_callbacks[0]()
    if auto:
        timer = fig.canvas.new_timer(interval=7000)
        timer.add_callback(auto_approve)
        timer.start()
    plt.show()
    if auto:
        try:
            timer.stop()
        except Exception:
            pass
    reviewed_cache.add(group_id)
    save_pickle_cache(REVIEWED_CACHE, reviewed_cache)
    return result

def get_filelist_hash(image_files):
    file_info = [(f, os.path.getmtime(f)) for f in image_files]
    return hashlib.sha256(str(sorted(file_info)).encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Interactively find and manage visually similar images in a directory.")
    parser.add_argument("directory", help="Directory containing images")
    parser.add_argument("--hash", choices=["phash", "ahash", "dhash", "whash"], default="phash",
                        help="Hash function to use (default: phash)")
    parser.add_argument("--threshold", type=int, default=5,
                        help="Hamming distance threshold for similarity (default: 5)")
    parser.add_argument("--auto", action="store_true", help="Automatically approve leftmost image after 7 seconds of no response")
    args = parser.parse_args()
    hash_methods = {
        'phash': imagehash.phash,
        'ahash': imagehash.average_hash,
        'dhash': imagehash.dhash,
        'whash': imagehash.whash
    }
    hasher = hash_methods.get(args.hash, imagehash.phash)
    exts = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.bmp', '.tiff', '.gif'}
    image_files = [str(p) for p in Path(args.directory).rglob('*') if p.suffix.lower() in exts and not p.name.startswith('._')]
    current_hash = get_filelist_hash(image_files)
    GROUPS_CACHE = Path(args.directory) / '.groups_cache.pkl'
    GROUPS_META = Path(args.directory) / '.groups_cache.meta'
    groups = []
    visited = set()
    # Only use cache for deleted files, not for file list hash
    if GROUPS_CACHE.exists():
        try:
            with open(GROUPS_CACHE, 'rb') as f:
                loaded = pickle.load(f)
                if isinstance(loaded, tuple) and len(loaded) == 2:
                    groups, visited = loaded
                else:
                    groups = loaded
                    visited = set()
        except Exception:
            groups = []
            visited = set()
        # Prune deleted files from groups and visited
        current_files = set(image_files)
        all_group_files = set(img for group in groups for img, _ in group)
        deleted_files = all_group_files - current_files
        if deleted_files:
            new_groups = []
            for group in groups:
                new_group = [(img, h) for img, h in group if img in current_files]
                if len(new_group) > 1:
                    new_groups.append(new_group)
            groups = new_groups
            visited = set(img for img in visited if img in current_files)
            with open(GROUPS_CACHE, 'wb') as f:
                pickle.dump((groups, visited), f)
            print(f"Pruned deleted files from cache. {len(groups)} groups remain.")
        # Invalidate cache only if new files are added
        cached_files = all_group_files
        new_files = current_files - cached_files
        if new_files:
            GROUPS_CACHE.unlink()
            print('Detected new files. Regenerating groups cache...')
            groups = []
            visited = set()
    hash_cache = load_hash_cache(args.directory, args.hash)
    hashes = []
    for img_path in tqdm(image_files, desc="Hashing images", unit="img"):
        stat = os.stat(img_path)
        cache_key = (img_path, stat.st_mtime)
        h = None
        if cache_key in hash_cache:
            h = hash_cache[cache_key]
        else:
            h = compute_hash(img_path, hasher)
            if h is not None:
                hash_cache[cache_key] = h
                save_hash_cache(args.directory, args.hash, hash_cache)
        if h is not None:
            hashes.append((img_path, h))
    # Only group ungrouped images, never regroup all
    grouped_imgs = set(img for group in groups for img, _ in group)
    ungrouped_imgs = [img for img in image_files if img not in grouped_imgs]
    if len(ungrouped_imgs) > 1:
        print(f"Grouping {len(ungrouped_imgs)} new/ungrouped images (this may take a while)...")
        ungrouped_hashes = [(img, h) for img, h in hashes if img in ungrouped_imgs]
        # Step 1: Build a hash-to-image index for ungrouped images
        hash_to_images = {}
        for img_path, h in hashes:
            if img_path in ungrouped_imgs:
                # Use the hash's string representation for dict key
                h_str = str(h)
                if h_str not in hash_to_images:
                    hash_to_images[h_str] = []
                hash_to_images[h_str].append((img_path, h))
        for i, (img1, hash1) in enumerate(tqdm(ungrouped_hashes, desc="Grouping images", unit="img")):
            if img1 in visited:
                continue
            group = [(img1, hash1)]
            h_str = str(hash1)
            # Check if hash matches any existing group
            if h_str in hash_to_images:
                for img2, hash2 in hash_to_images[h_str]:
                    if img2 not in visited and img2 != img1:
                        group.append((img2, hash2))
                        visited.add(img2)
            if len(group) > 1:
                for img, _ in group:
                    visited.add(img)
                groups.append(group)
            with open(GROUPS_CACHE, 'wb') as f:
                pickle.dump((groups, visited), f)
    else:
        print("No new groups to form. All remaining images are singletons.")
    print(f"Found {len(groups)} groups of visually similar images.")
    reviewed_cache = load_pickle_cache(REVIEWED_CACHE)
    deleted_cache = load_pickle_cache(DELETED_CACHE)
    deleted_files_log = Path(args.directory) / 'deleted_files.log'
    for idx, group in enumerate(groups):
        group_id = tuple(sorted(img for img, _ in group))
        if group_id in reviewed_cache:
            continue  # Already reviewed this group
        result = show_group_interactive(group, group_id, reviewed_cache, deleted_cache, auto=args.auto)
        if result['action'] == 'keep_one':
            for img_path, _ in group:
                if img_path != result['target']:
                    try:
                        os.remove(img_path)
                        deleted_cache.add(img_path)
                        with open(deleted_files_log, 'a') as dlog:
                            dlog.write(f"{img_path}\n")
                        print(f"Deleted {img_path}")
                    except Exception as e:
                        print(f"Failed to delete {img_path}: {e}")
            save_pickle_cache(DELETED_CACHE, deleted_cache)
            print(f"Kept {result['target']}")
        elif result['action'] == 'delete_all':
            for img_path, _ in group:
                try:
                    os.remove(img_path)
                    deleted_cache.add(img_path)
                    with open(deleted_files_log, 'a') as dlog:
                        dlog.write(f"{img_path}\n")
                    print(f"Deleted {img_path}")
                except Exception as e:
                    print(f"Failed to delete {img_path}: {e}")
            save_pickle_cache(DELETED_CACHE, deleted_cache)
        elif result['action'] == 'keep':
            print("Kept all images in this group.")
        else:
            print("No action taken.")

if __name__ == "__main__":
    main()
