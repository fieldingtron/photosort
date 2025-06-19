#!/usr/bin/env python3
"""
Simple photo management test script for Windows
Tests basic photo processing and management capabilities
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image, ExifTags
import exifread

def create_test_photos():
    """Create some test photos with different properties"""
    test_dir = Path("test_photos")
    test_dir.mkdir(exist_ok=True)
    
    photos = []
    
    # Create different test images
    test_data = [
        ("photo1.jpg", (1920, 1080), "red"),
        ("photo2.jpg", (800, 600), "green"),
        ("photo3.jpg", (640, 480), "blue"),
    ]
    
    for filename, size, color in test_data:
        img = Image.new('RGB', size, color=color)
        photo_path = test_dir / filename
        img.save(photo_path, quality=95)
        photos.append(photo_path)
        print(f"✓ Created {filename} ({size[0]}x{size[1]})")
    
    return photos

def analyze_photo(photo_path):
    """Analyze a single photo and extract information"""
    try:
        with Image.open(photo_path) as img:
            # Basic image info
            info = {
                'filename': photo_path.name,
                'size': img.size,
                'mode': img.mode,
                'format': img.format,
                'file_size': photo_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(photo_path.stat().st_mtime)
            }
            
            # Try to get EXIF data
            exif_dict = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                for tag, value in exif.items():
                    decoded = ExifTags.TAGS.get(tag, tag)
                    exif_dict[decoded] = value
            
            info['exif'] = exif_dict
            
            return info
            
    except Exception as e:
        print(f"Error analyzing {photo_path}: {e}")
        return None

def organize_photos_by_size(photos):
    """Organize photos into directories by size"""
    print("\nOrganizing photos by size...")
    
    # Create size-based directories
    size_dirs = {
        'small': Path("organized/small"),      # < 1000x1000
        'medium': Path("organized/medium"),    # 1000x1000 to 1920x1080
        'large': Path("organized/large")       # > 1920x1080
    }
    
    for size_dir in size_dirs.values():
        size_dir.mkdir(parents=True, exist_ok=True)
    
    for photo_path in photos:
        info = analyze_photo(photo_path)
        if info:
            width, height = info['size']
            max_dimension = max(width, height)
            
            if max_dimension < 1000:
                target_dir = size_dirs['small']
            elif max_dimension <= 1920:
                target_dir = size_dirs['medium']
            else:
                target_dir = size_dirs['large']
            
            # Copy photo to organized directory
            target_path = target_dir / photo_path.name
            shutil.copy2(photo_path, target_path)
            print(f"✓ Moved {photo_path.name} to {target_dir.name}/ ({width}x{height})")

def export_photo_info(photos):
    """Export photo information to a CSV file"""
    print("\nExporting photo information...")
    
    csv_path = Path("photo_inventory.csv")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        # Write header
        f.write("filename,width,height,file_size_kb,modified_date,format\n")
        
        for photo_path in photos:
            info = analyze_photo(photo_path)
            if info:
                width, height = info['size']
                file_size_kb = info['file_size'] // 1024
                modified = info['modified_time'].strftime('%Y-%m-%d %H:%M:%S')
                
                f.write(f"{info['filename']},{width},{height},{file_size_kb},{modified},{info['format']}\n")
        
        print(f"✓ Exported photo info to {csv_path}")

def cleanup_test_files():
    """Clean up test files and directories"""
    print("\nCleaning up test files...")
    
    paths_to_remove = [
        Path("test_photos"),
        Path("organized"),
        Path("photo_inventory.csv")
    ]
    
    for path in paths_to_remove:
        if path.exists():
            if path.is_file():
                path.unlink()
                print(f"✓ Removed file: {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                print(f"✓ Removed directory: {path}")

def main():
    """Main test function"""
    print("Photo Management Test Script")
    print("=" * 40)
    
    try:
        # Step 1: Create test photos
        print("Step 1: Creating test photos...")
        photos = create_test_photos()
        
        # Step 2: Analyze photos
        print("\nStep 2: Analyzing photos...")
        for photo_path in photos:
            info = analyze_photo(photo_path)
            if info:
                print(f"  {info['filename']}: {info['size'][0]}x{info['size'][1]} {info['format']} "
                      f"({info['file_size']} bytes)")
        
        # Step 3: Organize photos
        organize_photos_by_size(photos)
        
        # Step 4: Export information
        export_photo_info(photos)
        
        print("\n" + "=" * 40)
        print("✓ All tests completed successfully!")
        print("\nGenerated files:")
        print("  - test_photos/ (original test images)")
        print("  - organized/ (organized by size)")
        print("  - photo_inventory.csv (photo metadata)")
        
        # Ask if user wants to clean up
        response = input("\nClean up test files? (y/N): ").strip().lower()
        if response == 'y':
            cleanup_test_files()
        else:
            print("Test files preserved for inspection.")
        
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
