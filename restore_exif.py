#!/usr/bin/env python3
"""
Google Takeout EXIF Restoration Script

This script recursively processes Google Takeout photo directories and restores
EXIF metadata from the corresponding .supplemental-metadata.json files back
into the image files.
"""

import os
import json
import piexif
from PIL import Image
from datetime import datetime
import argparse
import sys


def parse_google_timestamp(timestamp_str):
    """
    Parse Google's timestamp format and return a datetime object.
    Google uses Unix timestamps as strings.
    """
    try:
        timestamp = int(timestamp_str)
        return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError):
        return None


def create_exif_dict(metadata):
    """
    Create an EXIF dictionary from Google's metadata.
    """
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Photo taken time
    if "photoTakenTime" in metadata and "timestamp" in metadata["photoTakenTime"]:
        dt = parse_google_timestamp(metadata["photoTakenTime"]["timestamp"])
        if dt:
            date_str = dt.strftime("%Y:%m:%d %H:%M:%S")
            exif_dict["0th"][piexif.ImageIFD.DateTime] = date_str
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = date_str
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
    
    # GPS coordinates
    if "geoData" in metadata:
        geo = metadata["geoData"]
        if "latitude" in geo and "longitude" in geo:
            lat = float(geo["latitude"])
            lon = float(geo["longitude"])
            
            # Convert to GPS format
            lat_deg = int(abs(lat))
            lat_min = int((abs(lat) - lat_deg) * 60)
            lat_sec = ((abs(lat) - lat_deg) * 60 - lat_min) * 60
            
            lon_deg = int(abs(lon))
            lon_min = int((abs(lon) - lon_deg) * 60)
            lon_sec = ((abs(lon) - lon_deg) * 60 - lon_min) * 60
            
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = [
                (lat_deg, 1), (lat_min, 1), (int(lat_sec * 100), 100)
            ]
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = [
                (lon_deg, 1), (lon_min, 1), (int(lon_sec * 100), 100)
            ]
            exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = "N" if lat >= 0 else "S"
            exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = "E" if lon >= 0 else "W"
            
            # Altitude if available
            if "altitude" in geo:
                alt = float(geo["altitude"])
                exif_dict["GPS"][piexif.GPSIFD.GPSAltitude] = (int(abs(alt) * 100), 100)
                exif_dict["GPS"][piexif.GPSIFD.GPSAltitudeRef] = 0 if alt >= 0 else 1
    
    # Title/Description
    if "title" in metadata:
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata["title"]
    
    # Camera make/model (if available in metadata)
    if "deviceInformation" in metadata:
        device_info = metadata["deviceInformation"]
        if "make" in device_info:
            exif_dict["0th"][piexif.ImageIFD.Make] = device_info["make"]
        if "model" in device_info:
            exif_dict["0th"][piexif.ImageIFD.Model] = device_info["model"]
    
    return exif_dict


def process_image(image_path, metadata_path, dry_run=False):
    """
    Process a single image file and restore its EXIF data.
    """
    try:
        # Read metadata
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Create EXIF dictionary
        exif_dict = create_exif_dict(metadata)
        
        # Skip if no useful metadata found
        if not any(exif_dict[key] for key in ["0th", "Exif", "GPS"]):
            print(f"  No useful metadata found for {os.path.basename(image_path)}")
            return False
        
        if dry_run:
            print(f"  Would restore EXIF data to {os.path.basename(image_path)}")
            return True
        
        # Create EXIF bytes
        exif_bytes = piexif.dump(exif_dict)
        
        # Open image and determine format
        with Image.open(image_path) as img:
            original_format = img.format
            
            # EXIF data is primarily supported by JPEG and TIFF formats
            if original_format in ('JPEG', 'TIFF'):
                # For JPEG/TIFF, preserve original format and add EXIF
                if img.mode in ("RGBA", "P") and original_format == 'JPEG':
                    # Convert to RGB for JPEG compatibility
                    img = img.convert("RGB")
                
                # Determine save parameters based on format
                if original_format == 'JPEG':
                    img.save(image_path, "JPEG", exif=exif_bytes, quality=95, optimize=True)
                elif original_format == 'TIFF':
                    img.save(image_path, "TIFF", exif=exif_bytes, compression='lzw')
            else:
                # For other formats that don't support EXIF well, 
                # we'll just update file timestamps based on the metadata
                if "photoTakenTime" in metadata and "timestamp" in metadata["photoTakenTime"]:
                    dt = parse_google_timestamp(metadata["photoTakenTime"]["timestamp"])
                    if dt:
                        timestamp = dt.timestamp()
                        os.utime(image_path, (timestamp, timestamp))
                        print(f"  ✓ Updated file timestamp for {os.path.basename(image_path)} (format: {original_format})")
                        return True
                else:
                    print(f"  ! Skipped {os.path.basename(image_path)} - format {original_format} doesn't support EXIF and no timestamp available")
                    return False
        
        print(f"  ✓ Restored EXIF data to {os.path.basename(image_path)}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {os.path.basename(image_path)}: {str(e)}")
        return False


def find_metadata_path(image_path):
    """
    Find the metadata file path for an image.
    For _edited files, try to find the metadata from the original file.
    """
    # First try the direct metadata file
    direct_metadata = image_path + ".supplemental-metadata.json"
    if os.path.exists(direct_metadata):
        return direct_metadata
    
    # If this is an edited file, try to find the original file's metadata
    if "-edited" in os.path.basename(image_path):
        original_path = image_path.replace("-edited", "")
        original_metadata = original_path + ".supplemental-metadata.json"
        if os.path.exists(original_metadata):
            return original_metadata
    
    return None


def process_directory(directory, dry_run=False):
    """
    Recursively process a directory and restore EXIF data to all images.
    """
    processed_count = 0
    error_count = 0
    
    # Supported image extensions
    image_extensions = {
        '.jpg', '.jpeg', '.JPG', '.JPEG',
        '.png', '.PNG',
        '.tiff', '.tif', '.TIFF', '.TIF',
        '.bmp', '.BMP',
        '.webp', '.WEBP',
        '.heic', '.HEIC',
        '.heif', '.HEIF',
        '.raw', '.RAW',
        '.cr2', '.CR2',
        '.nef', '.NEF',
        '.orf', '.ORF',
        '.arw', '.ARW',
        '.dng', '.DNG'
    }
    
    for root, dirs, files in os.walk(directory):
        print(f"\nProcessing directory: {root}")
        
        # Find all image files and their corresponding metadata files
        for file in files:
            if any(file.lower().endswith(ext.lower()) for ext in image_extensions):
                image_path = os.path.join(root, file)
                metadata_path = find_metadata_path(image_path)
                
                if metadata_path:
                    if "-edited" in file and metadata_path != image_path + ".supplemental-metadata.json":
                        print(f"  Using original file's metadata for {file}")
                    if process_image(image_path, metadata_path, dry_run):
                        processed_count += 1
                    else:
                        error_count += 1
                else:
                    print(f"  No metadata file found for {file}")
    
    return processed_count, error_count


def main():
    parser = argparse.ArgumentParser(description="Restore EXIF data to Google Takeout photos")
    parser.add_argument("directory", nargs="?", default="Google Photos", 
                       help="Directory to process (default: 'Google Photos')")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' not found!")
        sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
        print("=" * 50)
    
    print(f"Processing directory: {args.directory}")
    
    try:
        processed, errors = process_directory(args.directory, args.dry_run)
        
        print("\n" + "=" * 50)
        print(f"Processing complete!")
        print(f"Images processed: {processed}")
        print(f"Errors: {errors}")
        
        if args.dry_run:
            print("\nThis was a dry run. Use without --dry-run to actually modify files.")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
