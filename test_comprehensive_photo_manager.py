#!/usr/bin/env python3
"""
Real-world photo processing test script
Tests photo sorting, metadata extraction, and organization capabilities on Windows
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import csv

def create_sample_photo_with_metadata():
    """Create a single test photo with simulated metadata"""
    print("Creating sample photo with metadata...")
    
    # Create a sample image
    img = Image.new('RGB', (1600, 1200), color=(70, 130, 180))  # Steel blue
    
    # Add some text to make it identifiable
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to use a system font, fall back to default if not available
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    
    draw.text((50, 50), "Test Photo", fill=(255, 255, 255), font=font)
    draw.text((50, 100), f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
              fill=(255, 255, 255), font=font)
    
    # Save the image
    photo_path = Path("sample_photo.jpg")
    img.save(photo_path, "JPEG", quality=95)
    
    print(f"✓ Created sample photo: {photo_path}")
    return photo_path

def get_file_hash(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def extract_photo_metadata(photo_path):
    """Extract comprehensive metadata from a photo"""
    try:
        # File system metadata
        stat = photo_path.stat()
        metadata = {
            'filename': photo_path.name,
            'file_path': str(photo_path.absolute()),
            'file_size': stat.st_size,
            'created_time': datetime.fromtimestamp(stat.st_ctime),
            'modified_time': datetime.fromtimestamp(stat.st_mtime),
            'file_hash': get_file_hash(photo_path)
        }
        
        # Image metadata using PIL
        with Image.open(photo_path) as img:
            metadata.update({
                'width': img.width,
                'height': img.height,
                'mode': img.mode,
                'format': img.format,
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            })
            
            # Extract EXIF data
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
            
            metadata['exif'] = exif_data
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata from {photo_path}: {e}")
        return None

def test_duplicate_detection():
    """Test duplicate photo detection"""
    print("\nTesting duplicate detection...")
    
    # Create original photo
    original_path = create_sample_photo_with_metadata()
    
    # Create a copy (duplicate)
    duplicate_path = Path("duplicate_photo.jpg")
    shutil.copy2(original_path, duplicate_path)
    
    # Create a slightly different photo (not a duplicate)
    img = Image.new('RGB', (1600, 1200), color=(180, 70, 130))  # Different color
    different_path = Path("different_photo.jpg")
    img.save(different_path, "JPEG", quality=95)
    
    # Test hash-based duplicate detection
    photos = [original_path, duplicate_path, different_path]
    hashes = {}
    duplicates = []
    
    for photo in photos:
        file_hash = get_file_hash(photo)
        if file_hash in hashes:
            duplicates.append((photo, hashes[file_hash]))
        else:
            hashes[file_hash] = photo
    
    print(f"✓ Found {len(duplicates)} duplicate pairs")
    for duplicate, original in duplicates:
        print(f"  {duplicate.name} is a duplicate of {original.name}")
    
    return [original_path, duplicate_path, different_path]

def test_photo_organization():
    """Test organizing photos by date and properties"""
    print("\nTesting photo organization...")
    
    photos = test_duplicate_detection()
    
    # Create organized directory structure
    org_dir = Path("organized_photos")
    
    # Organize by file properties
    for photo in photos:
        metadata = extract_photo_metadata(photo)
        if metadata:
            # Organize by date
            created_date = metadata['created_time']
            year_month = created_date.strftime('%Y-%m')
            
            # Organize by size category
            width, height = metadata['width'], metadata['height']
            if width >= 1920 or height >= 1080:
                size_category = "high_res"
            elif width >= 800 or height >= 600:
                size_category = "medium_res"
            else:
                size_category = "low_res"
            
            # Create target directory
            target_dir = org_dir / year_month / size_category
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy photo
            target_path = target_dir / photo.name
            shutil.copy2(photo, target_path)
            
            print(f"✓ Organized {photo.name} -> {year_month}/{size_category}/")
    
    return photos

def export_photo_catalog():
    """Export a catalog of all processed photos"""
    print("\nExporting photo catalog...")
    
    # Find all photos in organized directory
    org_dir = Path("organized_photos")
    if not org_dir.exists():
        print("No organized photos found")
        return
    
    catalog_path = Path("photo_catalog.csv")
    
    with open(catalog_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'filename', 'relative_path', 'width', 'height', 'file_size_kb',
            'created_date', 'file_hash', 'size_category'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        photo_count = 0
        for photo_path in org_dir.rglob("*.jpg"):
            metadata = extract_photo_metadata(photo_path)
            if metadata:
                # Determine size category from path
                parts = photo_path.parts
                size_category = parts[-2] if len(parts) >= 2 else "unknown"
                
                writer.writerow({
                    'filename': metadata['filename'],
                    'relative_path': str(photo_path.relative_to(org_dir)),
                    'width': metadata['width'],
                    'height': metadata['height'],
                    'file_size_kb': metadata['file_size'] // 1024,
                    'created_date': metadata['created_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    'file_hash': metadata['file_hash'],
                    'size_category': size_category
                })
                photo_count += 1
        
        print(f"✓ Exported catalog of {photo_count} photos to {catalog_path}")

def main():
    """Main test function"""
    print("Real-world Photo Processing Test")
    print("=" * 50)
    print("This test demonstrates:")
    print("- Photo metadata extraction")
    print("- Duplicate detection")
    print("- Photo organization")
    print("- Catalog export")
    print("=" * 50)
    
    try:
        # Test basic functionality
        photos = test_photo_organization()
        
        # Export catalog
        export_photo_catalog()
        
        print("\n" + "=" * 50)
        print("✓ All photo processing tests completed successfully!")
        print("\nGenerated structure:")
        print("  📁 organized_photos/")
        print("    📁 YYYY-MM/")
        print("      📁 high_res/")
        print("      📁 medium_res/")
        print("      📁 low_res/")
        print("  📄 photo_catalog.csv")
        
        # Show directory structure
        org_dir = Path("organized_photos")
        if org_dir.exists():
            print(f"\nActual structure created:")
            for item in sorted(org_dir.rglob("*")):
                indent = "  " * len(item.relative_to(org_dir).parts)
                if item.is_dir():
                    print(f"{indent}📁 {item.name}/")
                else:
                    print(f"{indent}📄 {item.name}")
        
        # Ask about cleanup
        response = input(f"\nClean up test files? (y/N): ").strip().lower()
        if response == 'y':
            # Clean up
            cleanup_paths = [
                Path("sample_photo.jpg"),
                Path("duplicate_photo.jpg"), 
                Path("different_photo.jpg"),
                Path("organized_photos"),
                Path("photo_catalog.csv")
            ]
            
            for path in cleanup_paths:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    print(f"✓ Cleaned up: {path}")
        else:
            print("Test files preserved for inspection.")
        
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
