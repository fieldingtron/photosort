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

def set_exif_gps(img_path, lat, lon):
    try:
        exif_dict = piexif.load(str(img_path))
        if lat and lon:
            gps_ifd = exif_dict.get('GPS', {})
            gps_ifd[piexif.GPSIFD.GPSLatitude] = piexif.helper.GPSHelper.deg_to_dms_rational(abs(lat))
            gps_ifd[piexif.GPSIFD.GPSLatitudeRef] = b'N' if lat >= 0 else b'S'
            gps_ifd[piexif.GPSIFD.GPSLongitude] = piexif.helper.GPSHelper.deg_to_dms_rational(abs(lon))
            gps_ifd[piexif.GPSIFD.GPSLongitudeRef] = b'E' if lon >= 0 else b'W'
            exif_dict['GPS'] = gps_ifd
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, str(img_path))
    except Exception as e:
        print(f"Failed to set EXIF GPS for {img_path}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python restore_exif_from_json.py /path/to/GooglePhotosFolder")
        sys.exit(1)
    photo_dir = Path(sys.argv[1])
    if not photo_dir.is_dir():
        print(f"{photo_dir} is not a directory")
        sys.exit(1)
    for json_file in photo_dir.glob('*.json'):
        img_file = photo_dir / json_file.stem
        if img_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)
            timestamp = data.get('photoTakenTime', {}).get('timestamp')
            if timestamp:
                from datetime import datetime
                dt = datetime.fromtimestamp(int(timestamp))
                datetime_str = dt.strftime('%Y:%m:%d %H:%M:%S')
                set_exif_datetime(img_file, datetime_str)
            lat = data.get('geoData', {}).get('latitude')
            lon = data.get('geoData', {}).get('longitude')
            if lat and lon and lat != 0.0 and lon != 0.0:
                set_exif_gps(img_file, lat, lon)
            print(f"Wrote EXIF to {img_file}")

if __name__ == "__main__":
    main()
