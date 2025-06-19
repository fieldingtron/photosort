#!/usr/bin/env python3
"""
Test script for photo management tools on Windows
Since osxphotos is macOS/Linux only, this script tests alternative photo management tools
"""

import os
import sys
import subprocess
from pathlib import Path
import time

def test_pillow():
    """Test Pillow (PIL) for basic image processing"""
    print("Testing Pillow (PIL)...")
    try:
        from PIL import Image, ExifTags
        from PIL.ExifTags import TAGS
        
        # Test basic functionality
        print("✓ Pillow imported successfully")
        
        # Create a simple test image
        test_image = Image.new('RGB', (100, 100), color='red')
        test_path = "test_image.jpg"
        test_image.save(test_path)
        
        # Try to read it back
        loaded_image = Image.open(test_path)
        print(f"✓ Created and loaded test image: {loaded_image.size}")
        
        # Clean up
        os.remove(test_path)
        
        return True
    except Exception as e:
        print(f"✗ Pillow test failed: {e}")
        return False

def test_exifread():
    """Test exifread for EXIF data extraction"""
    print("\nTesting exifread...")
    try:
        import exifread
        print("✓ exifread imported successfully")
        return True
    except ImportError:
        print("✗ exifread not installed")
        return False
    except Exception as e:
        print(f"✗ exifread test failed: {e}")
        return False

def test_send2trash():
    """Test send2trash for safe file deletion"""
    print("\nTesting send2trash...")
    try:
        from send2trash import send2trash
        print("✓ send2trash imported successfully")
        
        # Create a test file and send to trash
        test_file = "test_delete.txt"
        with open(test_file, 'w') as f:
            f.write("test")
        
        send2trash(test_file)
        print("✓ Successfully sent test file to trash")
        return True
    except ImportError:
        print("✗ send2trash not installed")
        return False
    except Exception as e:
        print(f"✗ send2trash test failed: {e}")
        return False

def test_pathlib():
    """Test pathlib for path operations"""
    print("\nTesting pathlib...")
    try:
        from pathlib import Path
        
        # Test basic path operations
        current_dir = Path.cwd()
        print(f"✓ Current directory: {current_dir}")
        
        # Test path manipulation
        test_path = Path("test") / "folder" / "image.jpg"
        print(f"✓ Path manipulation works: {test_path}")
        
        return True
    except Exception as e:
        print(f"✗ pathlib test failed: {e}")
        return False

def create_sample_test():
    """Create a sample photo processing function"""
    print("\nCreating sample photo processing test...")
    
    try:
        from PIL import Image
        import time
        
        # Create a sample image with metadata
        img = Image.new('RGB', (800, 600), color='blue')
        
        # Add some basic "EXIF" info (simulated)
        sample_path = "sample_photo_test.jpg"
        img.save(sample_path, quality=95)
        
        # Read it back and get info
        with Image.open(sample_path) as img:
            print(f"✓ Sample image created: {img.size}, mode: {img.mode}")
            print(f"✓ Format: {img.format}")
        
        # Clean up
        os.remove(sample_path)
        
        print("✓ Sample photo processing test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Sample test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Testing photo management tools on Windows")
    print("=" * 50)
    
    # Test virtual environment
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print()
    
    tests = [
        test_pathlib,
        test_pillow,
        test_exifread,
        test_send2trash,
        create_sample_test
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your environment is ready for photo processing.")
    else:
        print("⚠️  Some tests failed. Check the output above for missing dependencies.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
