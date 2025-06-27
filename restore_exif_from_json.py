#!/usr/bin/env python3
"""
Restore EXIF metadata to images from Google Takeout JSON files (Python version).

Requirements:
- piexif
- Pillow
- jq (for advanced JSON parsing, but not required for basic fields)

Usage:
    python restore_exif_from_json.py /path/to/GooglePhotosFolder
"""
import os
import sys
import json
from pathlib import Path
import piexif
from PIL import Image

def set_exif_datetime(img_path, datetime_str):
    try:
        exif_dict = piexif.load(str(img_path))
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = datetime_str.encode('utf-8')
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(img_path))
    except Exception as e:
        print(f"Failed to set EXIF datetime for {img_path}: {e}")

def deg_to_dms_rational(deg):
    # Converts decimal degrees to EXIF DMS rational format
    d = int(deg)
    m = int((deg - d) * 60)
    s = float((deg - d - m/60) * 3600)
    return [
        (abs(d), 1),
        (abs(m), 1),
        (int(round(abs(s * 10000))), 10000)
    ]

def set_exif_gps(img_path, lat, lon):
    try:
        exif_dict = piexif.load(str(img_path))
        if lat and lon:
            gps_ifd = exif_dict.get('GPS', {})
            gps_ifd[piexif.GPSIFD.GPSLatitude] = deg_to_dms_rational(abs(lat))
            gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = b'N' if lat >= 0 else b'S'
            gps_ifd[piexif.GPSIFD.GPSLongitude] = deg_to_dms_rational(abs(lon))
            gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = b'E' if lon >= 0 else b'W'
            exif_dict['GPS'] = gps_ifd
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(img_path))
    except Exception as e:
        print(f"Failed to set EXIF GPS for {img_path}: {e}")

def set_exif_orientation(img_path, orientation):
    try:
        exif_dict = piexif.load(str(img_path))
        exif_dict['0th'][piexif.ImageIFD.Orientation] = orientation
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(img_path))
    except Exception as e:
        print(f"Failed to set EXIF orientation for {img_path}: {e}")

def set_mp4_metadata(mp4_path, datetime_str=None, lat=None, lon=None):
    # Use ffmpeg to set creation_time and GPS metadata if available
    import shutil
    if not shutil.which('ffmpeg'):
        print(f"ffmpeg not found, cannot update metadata for {mp4_path}")
        return
    cmd = ['ffmpeg', '-y', '-i', str(mp4_path)]
    metadata_args = []
    if datetime_str:
        metadata_args += ['-metadata', f'creation_time={datetime_str}']
    if lat and lon:
        # GPS coordinates in ISO 6709 format: "+37.785833-122.406417/"
        gps_str = f"{lat:+09.6f}{lon:+010.6f}/"
        metadata_args += ['-metadata', f'location={gps_str}']
    if not metadata_args:
        return
    tmp_path = str(mp4_path) + '.tmp.mp4'
    cmd += metadata_args + ['-codec', 'copy', tmp_path]
    import subprocess
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.replace(tmp_path, mp4_path)
        #print(f"Updated MP4 metadata for {mp4_path}")
    except Exception as e:
        print(f"Failed to update MP4 metadata for {mp4_path}: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python restore_exif_from_json.py /path/to/GooglePhotosFolder")
        sys.exit(1)
    photo_dir = Path(sys.argv[1])
    if not photo_dir.is_dir():
        print(f"{photo_dir} is not a directory")
        sys.exit(1)
    # Recursively find all .json files
    json_files = list(photo_dir.rglob('*.json'))
    total = len(json_files)
    if total == 0:
        print("No .json files found in the specified directory or subdirectories.")
        sys.exit(1)
    updated_count = 0
    not_found_count = 0
    for idx, json_file in enumerate(json_files, 1):
        # Handle Google Takeout naming: strip .supplemental-metadata.json or .metadata.json
        name = json_file.name
        if name.endswith('.supplemental-metadata.json'):
            base_name = name[:-len('.supplemental-metadata.json')]
        elif name.endswith('.metadata.json'):
            base_name = name[:-len('.metadata.json')]
        elif name.endswith('.json'):
            base_name = name[:-len('.json')]
        else:
            base_name = name
        # Try to find the base file and -edited variant
        base_file = json_file.parent / base_name
        edited_file = json_file.parent / (Path(base_name).stem + "-edited" + Path(base_name).suffix)
        img_file = None
        if base_file.exists():
            img_file = base_file
        elif edited_file.exists():
            img_file = edited_file
        if img_file and img_file.exists():
            ext = img_file.suffix.lower()
            with open(json_file, 'r') as f:
                data = json.load(f)
            timestamp = data.get('photoTakenTime', {}).get('timestamp')
            datetime_str = None
            if timestamp:
                from datetime import datetime
                dt = datetime.fromtimestamp(int(timestamp))
                datetime_str = dt.strftime('%Y:%m:%d %H:%M:%S')
            lat = data.get('geoData', {}).get('latitude')
            lon = data.get('geoData', {}).get('longitude')
            orientation = data.get('photoTakenExifOrientation') or data.get('photoTakenExif', {}).get('orientation')
            # JPEG/EXIF
            if ext in ['.jpg', '.jpeg']:
                if datetime_str:
                    set_exif_datetime(img_file, datetime_str)
                if lat and lon and lat != 0.0 and lon != 0.0:
                    set_exif_gps(img_file, lat, lon)
                if orientation:
                    try:
                        set_exif_orientation(img_file, int(orientation))
                    except Exception:
                        pass
            # MP4
            elif ext == '.mp4':
                iso_datetime = None
                if timestamp:
                    from datetime import datetime, timezone
                    dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    iso_datetime = dt.isoformat().replace('+00:00', 'Z')
                set_mp4_metadata(img_file, iso_datetime, lat, lon)
            updated_count += 1
        else:
            not_found_count += 1
        print(f"\r{updated_count}/{total} files updated", end="", flush=True)
    print(f"\nDone. {updated_count} of {total} JSON files had matching media updated.")
    if not_found_count > 0:
        print(f"WARNING: {not_found_count} JSON files had no matching media file and could not be updated.")

if __name__ == "__main__":
    main()
