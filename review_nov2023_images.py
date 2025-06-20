"""
Script to review all images created in November 2023 in a directory.
For each image, pops up a window with the image and two buttons:
- A black 'Keep' button
- A red 'Delete?' button

Checks EXIF 'DateTimeOriginal' if available, otherwise falls back to file modification time.

Requirements:
- pillow, pillow-heif, matplotlib, piexif

Usage:
    python review_nov2023_images.py /path/to/image_dir
"""

import os
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import argparse
import datetime
import piexif

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("Warning: pillow-heif not installed. HEIC images may not be supported.")

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.bmp', '.tiff', '.tif'}

def get_exif_datetime(path, exif_cache=None):
    if exif_cache is not None:
        cache_key = str(path), path.stat().st_mtime
        if cache_key in exif_cache:
            return exif_cache[cache_key]
    try:
        img = Image.open(path)
        exif = img.info.get('exif')
        if exif:
            exif_dict = piexif.load(exif)
            dt_bytes = exif_dict['Exif'].get(piexif.ExifIFD.DateTimeOriginal)
            if dt_bytes:
                dt_str = dt_bytes.decode('utf-8')
                dt = datetime.datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                if exif_cache is not None:
                    exif_cache[cache_key] = dt
                return dt
    except Exception:
        pass
    ts = path.stat().st_mtime
    dt = datetime.datetime.fromtimestamp(ts)
    if exif_cache is not None:
        exif_cache[cache_key] = dt
    return dt

def get_november_2023_images(directory, exif_cache=None):
    from tqdm import tqdm
    files = [f for f in Path(directory).iterdir() if f.suffix.lower() in SUPPORTED_EXTS and f.is_file() and not f.name.startswith('._')]
    nov2023 = []
    for f in tqdm(files, desc="Searching for Nov 2023 images", unit="file"):
        dt = get_exif_datetime(f, exif_cache)
        if dt.year == 2023 and dt.month == 11:
            nov2023.append(f)
    return sorted(nov2023)

def review_image(path):
    import matplotlib.widgets as mwidgets
    fig, ax = plt.subplots(figsize=(7, 7))
    img = Image.open(path)
    dt = get_exif_datetime(path)
    ax.imshow(img)
    ax.set_title(f"{os.path.basename(path)}\nDate: {dt}")
    ax.axis('off')
    plt.tight_layout(rect=[0, 0.15, 1, 0.95])

    # Add buttons
    ax_keep = plt.axes([0.25, 0.03, 0.2, 0.08])
    ax_delete = plt.axes([0.55, 0.03, 0.2, 0.08])
    btn_keep = mwidgets.Button(ax_keep, 'Keep', color='black', hovercolor='gray')
    btn_delete = mwidgets.Button(ax_delete, 'Delete?', color='red', hovercolor='tomato')
    result = {'action': 'keep'}

    def on_keep(event):
        result['action'] = 'keep'
        plt.close(fig)
    def on_delete(event):
        result['action'] = 'delete'
        plt.close(fig)
    btn_keep.on_clicked(on_keep)
    btn_delete.on_clicked(on_delete)

    plt.show()
    return result['action']

def load_exif_cache(directory):
    import pickle
    cache_path = Path(directory) / '.exif_cache.pkl'
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_exif_cache(directory, cache):
    import pickle
    cache_path = Path(directory) / '.exif_cache.pkl'
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f)

def load_reviewed_cache(directory):
    import pickle
    cache_path = Path(directory) / '.reviewed_cache.pkl'
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return set()
    return set()

def save_reviewed_cache(directory, cache):
    import pickle
    cache_path = Path(directory) / '.reviewed_cache.pkl'
    with open(cache_path, 'wb') as f:
        pickle.dump(cache, f)

def main():
    parser = argparse.ArgumentParser(description="Review all images created in November 2023 in a directory.")
    parser.add_argument("directory", help="Directory containing images")
    args = parser.parse_args()

    exif_cache = load_exif_cache(args.directory)
    reviewed_cache = load_reviewed_cache(args.directory)
    images = get_november_2023_images(args.directory, exif_cache)
    save_exif_cache(args.directory, exif_cache)
    print(f"Found {len(images)} images from November 2023.")
    from tqdm import tqdm
    for img_path in tqdm(images, desc="Reviewing images", unit="img"):
        if str(img_path) in reviewed_cache:
            continue  # Skip already reviewed
        action = review_image(img_path)
        if action == 'delete':
            os.remove(img_path)
            print(f"Deleted {img_path}")
        else:
            print(f"Kept {img_path}")
        reviewed_cache.add(str(img_path))
        save_exif_cache(args.directory, exif_cache)
        save_reviewed_cache(args.directory, reviewed_cache)

if __name__ == "__main__":
    main()
