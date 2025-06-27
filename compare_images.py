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

# Auto-activate virtual environment if not already active
import sys
import os
from pathlib import Path

def auto_activate_venv():
    """Automatically activate virtual environment if not already active"""
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return  # Already in a virtual environment
    
    # Look for venv in current directory or parent directories
    current_dir = Path(__file__).parent
    venv_paths_to_try = [
        current_dir / "venv",
        current_dir / ".venv",
        current_dir.parent / "venv",
        current_dir.parent / ".venv"
    ]
    
    for venv_path in venv_paths_to_try:
        if venv_path.exists():
            # Determine the activation script path based on OS
            if os.name == 'nt':  # Windows
                activate_script = venv_path / "Scripts" / "activate.bat"
                python_exe = venv_path / "Scripts" / "python.exe"
            else:  # Unix/Linux/macOS
                activate_script = venv_path / "bin" / "activate"
                python_exe = venv_path / "bin" / "python"
            
            if python_exe.exists():
                # Re-execute the script with the virtual environment Python
                import subprocess
                print(f"🐍 Activating virtual environment: {venv_path}")
                try:
                    # Pass all original arguments to the venv Python
                    result = subprocess.run([str(python_exe)] + sys.argv, check=True)
                    sys.exit(result.returncode)
                except subprocess.CalledProcessError as e:
                    sys.exit(e.returncode)
                except KeyboardInterrupt:
                    sys.exit(1)
    
    # If no venv found, continue with system Python but warn user
    print("⚠️  No virtual environment found. Make sure required packages are installed:")
    print("   pip install pillow pillow-heif matplotlib imagehash tqdm")
    print()

# Try to activate venv before importing other modules
auto_activate_venv()

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
import stat
import glob

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
    try:
        with open(path, 'wb') as f:
            pickle.dump(cache, f)
    except PermissionError:
        print(f"⚠️  Warning: Cannot write to {path} (permission denied)")
        # Try to save to a temp directory or user's home directory
        fallback_path = Path.home() / f".photosort_cache_{Path(path).name}"
        try:
            with open(fallback_path, 'wb') as f:
                pickle.dump(cache, f)
            print(f"📁 Cache saved to fallback location: {fallback_path}")
        except Exception as e:
            print(f"❌ Failed to save cache to fallback location: {e}")
    except Exception as e:
        print(f"❌ Error saving cache to {path}: {e}")

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
    try:
        if cache_path.exists():
            os.chmod(cache_path, stat.S_IWRITE)
        with open(cache_path, 'wb') as f:
            pickle.dump(cache, f)
    except PermissionError:
        print(f"⚠️  Warning: Cannot write to {cache_path} (permission denied)")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error saving hash cache to {cache_path}: {e}")
        import sys
        sys.exit(1)

def show_group_interactive(group, group_id, reviewed_cache, deleted_cache, auto=None):
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
    # Auto-approve leftmost after N seconds if auto is set (auto is int seconds)
    def auto_approve(event=None):
        if not action_taken[0]:
            keep_callbacks[0]()
    if isinstance(auto, int) and auto > 0:
        timer = fig.canvas.new_timer(interval=auto * 1000)  # N seconds
        timer.add_callback(auto_approve)
        timer.start()
    plt.show()
    if isinstance(auto, int) and auto > 0:
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

def ensure_cache_files_writable(directory, hash_name=None):
    import glob
    import sys
    from pathlib import Path
    import stat
    cache_files = [
        Path(directory) / '.groups_cache.pkl',
        Path(directory) / '.groups_cache.meta',
        Path(directory) / '.reviewed_groups.pkl',
        Path(directory) / '.deleted_images.pkl',
    ]
    # Add all .hash_cache_*.pkl files
    cache_files += [Path(f) for f in glob.glob(str(Path(directory) / '.hash_cache_*.pkl'))]
    # Always include the expected hash cache file
    hash_cache = None
    if hash_name:
        hash_cache = Path(directory) / f'.hash_cache_{hash_name}.pkl'
        if hash_cache not in cache_files:
            cache_files.append(hash_cache)
        # If it doesn't exist, create it empty
        if not hash_cache.exists():
            try:
                with open(hash_cache, 'wb') as f:
                    import pickle
                    pickle.dump({}, f)
                print(f"Created empty hash cache file: {hash_cache}")
            except Exception as e:
                print(f"❌ Could not create hash cache file {hash_cache}: {e}")
                sys.exit(1)
    for cache_file in cache_files:
        # Only check files that exist, or the hash cache file (which is always created above)
        if not cache_file.exists() and (hash_cache is None or cache_file != hash_cache):
            continue
        if cache_file.exists():
            try:
                # Try opening for append (does not truncate)
                with open(cache_file, 'ab'):
                    pass
            except PermissionError:
                print(f"Cache file {cache_file} is not writable. Attempting to remove read-only attribute...")
                try:
                    os.chmod(cache_file, stat.S_IWRITE)
                    with open(cache_file, 'ab'):
                        pass
                    print(f"Successfully made {cache_file} writable.")
                except Exception as e:
                    print(f"Failed to remove read-only attribute with os.chmod: {e}")
                    # Try using attrib command on Windows
                    if os.name == 'nt':
                        import subprocess
                        try:
                            subprocess.run(["attrib", "-R", str(cache_file)], check=True)
                            with open(cache_file, 'ab'):
                                pass
                            print(f"Successfully made {cache_file} writable using attrib.")
                        except Exception as e2:
                            print(f"❌ Cannot make {cache_file} writable even with attrib: {e2}")
                    else:
                        print(f"❌ Cannot make {cache_file} writable: {e}")
        # Test write and read
        try:
            test_data = {'test': 123}
            import pickle
            with open(cache_file, 'wb') as f:
                pickle.dump(test_data, f)
            with open(cache_file, 'rb') as f:
                loaded = pickle.load(f)
            if loaded.get('test') != 123:
                print(f"❌ Test write/read failed for {cache_file}")
                # Try to delete the file and log
                try:
                    os.remove(cache_file)
                    print(f"🗑️  Deleted cache file after failed test write/read: {cache_file}")
                except Exception as del_exc:
                    print(f"❌ Could not delete {cache_file} after failed test write/read: {del_exc}")
                sys.exit(1)
            print(f"Test write/read succeeded for {cache_file}")
            # Restore empty dict if this is a hash cache
            if cache_file.name.startswith('.hash_cache_'):
                with open(cache_file, 'wb') as f:
                    pickle.dump({}, f)
        except Exception as e:
            print(f"❌ Test write/read failed for {cache_file}: {e}")
            # Try to delete the file and log
            try:
                os.remove(cache_file)
                print(f"🗑️  Deleted cache file after failed test write/read: {cache_file}")
            except Exception as del_exc:
                print(f"❌ Could not delete {cache_file} after failed test write/read: {del_exc}")
            sys.exit(1)

# When moving or keeping images, move from import to primary if needed
def move_to_primary(img_path, dest_directory):
        import shutil
        dest_dir = Path(dest_directory)
        src_path = Path(img_path)
        dest_path = dest_dir / src_path.name
        if src_path.resolve() == dest_path.resolve():
            return str(dest_path)
        # Avoid overwriting
        if dest_path.exists():
            base, ext = os.path.splitext(dest_path.name)
            for i in range(1, 10000):
                candidate = dest_dir / f"{base}_imported_{i}{ext}"
                if not candidate.exists():
                    dest_path = candidate
                    break
        shutil.move(str(src_path), str(dest_path))
        print(f"Moved {src_path} to {dest_path}")
        return str(dest_path)

def main():
    parser = argparse.ArgumentParser(description="Interactively find and manage visually similar images in a directory.")
    parser.add_argument("directory", help="Directory containing images (primary destination)")
    parser.add_argument("--hash", choices=["phash", "ahash", "dhash", "whash"], default="phash",
                        help="Hash function to use (default: phash)")
    parser.add_argument("--threshold", type=int, default=5,
                        help="Hamming distance threshold for similarity (default: 5)")
    parser.add_argument("--auto", nargs="?", const=10, type=int,
                        help="Automatically approve leftmost image after N seconds of no response (default: 10s if used without value)")
    parser.add_argument("--no-gui", action="store_true",
                        help="If set, automatically choose the leftmost image in each group and delete the others, without showing any window.")
    parser.add_argument("--import", dest="import_dir", type=str, default=None,
                        help="Import images from another directory recursively, comparing and moving unique/selected images to the primary directory.")
    args = parser.parse_args()
    # Ensure all cache files are writable before proceeding
    ensure_cache_files_writable(args.directory, args.hash)
    hash_methods = {
        'phash': imagehash.phash,
        'ahash': imagehash.average_hash,
        'dhash': imagehash.dhash,
        'whash': imagehash.whash
    }
    hasher = hash_methods.get(args.hash, imagehash.phash)
    exts = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.bmp', '.tiff', '.gif'}
    # Gather images from both primary and import directories
    image_files = [str(p) for p in Path(args.directory).rglob('*') if p.suffix.lower() in exts and not p.name.startswith('._')]
    image_sources = {img: 'primary' for img in image_files}
    if args.import_dir:
        import_files = [str(p) for p in Path(args.import_dir).rglob('*') if p.suffix.lower() in exts and not p.name.startswith('._')]
        for img in import_files:
            if img not in image_sources:
                image_files.append(img)
                image_sources[img] = 'import'
    current_hash = get_filelist_hash(image_files)
    GROUPS_CACHE = Path(args.directory) / '.groups_cache.pkl'
    GROUPS_META = Path(args.directory) / '.groups_cache.meta'
    groups = []
    visited = set()
    # Only use cache for deleted files, not for file list hash
    start_total = time.time()
    print(f"Looking for cache file: {GROUPS_CACHE}")
    cache_start = time.time()
    if GROUPS_CACHE.exists():
        print(f"Cache file found: {GROUPS_CACHE}. Attempting to load...")
        try:
            with open(GROUPS_CACHE, 'rb') as f:
                loaded = pickle.load(f)
                if isinstance(loaded, tuple) and len(loaded) == 2:
                    groups, visited = loaded
                else:
                    groups = loaded
                    visited = set()
            print(f"Cache loaded successfully. {len(groups)} groups loaded. (took {time.time() - cache_start:.2f}s)")
        except Exception as e:
            print(f"Failed to load cache file: {e} (after {time.time() - cache_start:.2f}s)")
            groups = []
            visited = set()
    else:
        print(f"No cache file found. Will compute groups from scratch. (took {time.time() - cache_start:.2f}s)")
    # Prune deleted files from groups and visited
    # Filter out any group that is not a list of (img, hash) tuples
    def is_valid_group(group):
        return isinstance(group, (list, tuple)) and all(isinstance(item, (list, tuple)) and len(item) == 2 for item in group)
    valid_groups = []
    invalid_group_count = 0
    for group in groups:
        if is_valid_group(group):
            valid_groups.append(group)
        else:
            print(f"⚠️  Skipping invalid group in cache: {group}")
            invalid_group_count += 1
    if invalid_group_count > 0:
        print(f"⚠️  {invalid_group_count} invalid group(s) found and skipped in cache.")
    groups = valid_groups
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
        try:
            # Remove read-only attribute before writing
            if GROUPS_CACHE.exists():
                os.chmod(GROUPS_CACHE, stat.S_IWRITE)
            with open(GROUPS_CACHE, 'wb') as f:
                pickle.dump((groups, visited), f)
            print(f"Pruned deleted files from cache. {len(groups)} groups remain.")
        except PermissionError:
            print(f"⚠️  Warning: Cannot write to {GROUPS_CACHE} (permission denied)")
            # Try to save to a temp directory or user's home directory
            fallback_path = Path.home() / f".photosort_cache_{GROUPS_CACHE.name}"
            try:
                with open(fallback_path, 'wb') as f:
                    pickle.dump((groups, visited), f)
                print(f"📁 Cache saved to fallback location: {fallback_path}")
            except Exception as e:
                print(f"❌ Failed to save cache to fallback location: {e}")
    # Invalidate cache only if new files are added
    cached_files = all_group_files
    new_files = current_files - cached_files
    if new_files:
        if GROUPS_CACHE.exists():
            os.chmod(GROUPS_CACHE, stat.S_IWRITE)
            GROUPS_CACHE.unlink()
        print('Detected new files. Regenerating groups cache...')
        groups = []
        visited = set()
    print(f"Preparing to hash {len(image_files)} images...")
    hash_start = time.time()
    hash_cache = load_hash_cache(args.directory, args.hash)
    hashes = []
    hash_cache_updated = False  # Track if cache was updated
    for i, img_path in enumerate(tqdm(image_files, desc="Hashing images", unit="img")):
        if i % 100 == 0 and i > 0:
            print(f"  Hashed {i} images so far... ({time.time() - hash_start:.2f}s elapsed)")
        img_stat = os.stat(img_path)
        cache_key = (img_path, img_stat.st_mtime)
        h = None
        if cache_key in hash_cache:
            h = hash_cache[cache_key]
        else:
            h = compute_hash(img_path, hasher)
            if h is not None:
                hash_cache[cache_key] = h
                hash_cache_updated = True
        if h is not None:
            hashes.append((img_path, h))
        # Save every 100 images if there are updates
        if i > 0 and i % 100 == 0 and hash_cache_updated:
            save_hash_cache(args.directory, args.hash, hash_cache)
            hash_cache_updated = False
    # Save hash cache only if updated at the end
    if hash_cache_updated:
        save_hash_cache(args.directory, args.hash, hash_cache)
    print(f"Hashing complete. ({time.time() - hash_start:.2f}s)")
    # Only group ungrouped images, never regroup all
    grouped_imgs = set(img for group in groups for img, _ in group)
    ungrouped_imgs = [img for img in image_files if img not in grouped_imgs]
    group_start = time.time()
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
        print(f"Grouping complete. ({time.time() - group_start:.2f}s)")
    else:
        print("No new groups to form. All remaining images are singletons.")
    print(f"Found {len(groups)} groups of visually similar images.")
    review_start = time.time()
    reviewed_cache = load_pickle_cache(REVIEWED_CACHE)
    deleted_cache = load_pickle_cache(DELETED_CACHE)
    deleted_files_log = Path(args.directory) / 'deleted_files.log'
    for idx, group in enumerate(groups):
        group_id = tuple(sorted(img for img, _ in group))
        if group_id in reviewed_cache:
            continue  # Already reviewed this group
        auto_timeout = args.auto if args.auto is not None else None
        if args.no_gui:
            # Simulate auto-choose leftmost without window
            result = {'action': 'keep_one', 'target': group[0][0]}
            reviewed_cache.add(group_id)
            save_pickle_cache(REVIEWED_CACHE, reviewed_cache)
        else:
            result = show_group_interactive(group, group_id, reviewed_cache, deleted_cache, auto=auto_timeout)
        if result['action'] == 'keep_one':
            # If the kept image is from import, move it to primary
            kept = result['target']
            if image_sources.get(kept) == 'import':
                new_path = move_to_primary(kept, args.directory)
                # Update caches and group references
                result['target'] = new_path
                image_sources[new_path] = 'primary'
                image_sources.pop(kept, None)
                kept = new_path
            for img_path, _ in group:
                if img_path != result['target']:
                    try:
                        # Remove read-only attribute before deleting
                        if os.path.exists(img_path):
                            os.chmod(img_path, stat.S_IWRITE)
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
                    # Remove read-only attribute before deleting
                    if os.path.exists(img_path):
                        os.chmod(img_path, stat.S_IWRITE)
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
    # After all groups, move any unique images from import to primary
    unique_imports = [img for img in image_files if image_sources.get(img) == 'import' and img not in deleted_cache]
    for img in unique_imports:
        move_to_primary(img, args.directory)
    print(f"Review loop complete. ({time.time() - review_start:.2f}s)")
    print(f"Total script time: {time.time() - start_total:.2f}s")

if __name__ == "__main__":
    main()
