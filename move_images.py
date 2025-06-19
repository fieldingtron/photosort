#!/usr/bin/env python3
"""
Script to recursively move image files from Downloads folder to ~/PhotoExport.
Files that don't match image extensions are moved to ~/NoMatch.
"""

import os
import shutil
import argparse
from pathlib import Path

# Common image file extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.webp', '.svg', '.ico', '.raw', '.cr2', '.nef', '.orf',
    '.arw', '.dng', '.psd', '.heic', '.heif', '.avif'
}

def is_image_file(file_path):
    """Check if a file is an image based on its extension."""
    return file_path.suffix.lower() in IMAGE_EXTENSIONS

def create_directories():
    """Create the destination directories if they don't exist."""
    photo_export = Path.home() / "PhotoExport"
    no_match = Path.home() / "NoMatch"
    
    photo_export.mkdir(exist_ok=True)
    no_match.mkdir(exist_ok=True)
    
    return photo_export, no_match

def move_file_with_conflict_resolution(src, dst_dir):
    """Move a file to destination directory, handling name conflicts."""
    dst = dst_dir / src.name
    
    # If file already exists, add a number to make it unique
    counter = 1
    original_stem = src.stem
    original_suffix = src.suffix
    
    while dst.exists():
        new_name = f"{original_stem}_{counter}{original_suffix}"
        dst = dst_dir / new_name
        counter += 1
    
    shutil.move(str(src), str(dst))
    return dst

def process_downloads_folder(downloads_path, dry_run=False, verbose=False):
    """Recursively process all files in the Downloads folder."""
    downloads_path = Path(downloads_path)
    
    if not downloads_path.exists():
        print(f"Error: Downloads folder '{downloads_path}' does not exist.")
        return
    
    photo_export, no_match = create_directories()
    
    image_count = 0
    other_count = 0
    error_count = 0
    
    print(f"Processing files in: {downloads_path}")
    print(f"Image files will go to: {photo_export}")
    print(f"Other files will go to: {no_match}")
    
    if dry_run:
        print("\n--- DRY RUN MODE - No files will be moved ---")
    
    print("\nProcessing files...")
    
    # Recursively walk through all files
    for root, dirs, files in os.walk(downloads_path):
        root_path = Path(root)
        
        for file in files:
            file_path = root_path / file
            
            try:
                if is_image_file(file_path):
                    destination = photo_export
                    file_type = "IMAGE"
                    image_count += 1
                else:
                    destination = no_match
                    file_type = "OTHER"
                    other_count += 1
                
                if verbose or dry_run:
                    print(f"[{file_type}] {file_path} -> {destination}")
                
                if not dry_run:
                    moved_to = move_file_with_conflict_resolution(file_path, destination)
                    if verbose:
                        print(f"  Moved to: {moved_to}")
                
            except Exception as e:
                error_count += 1
                print(f"ERROR processing {file_path}: {e}")
    
    print(f"\nSummary:")
    print(f"  Image files: {image_count}")
    print(f"  Other files: {other_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total files processed: {image_count + other_count}")
    
    if dry_run:
        print("\nThis was a dry run. Use --execute to actually move the files.")

def main():
    parser = argparse.ArgumentParser(description='Move image files from Downloads to PhotoExport')
    parser.add_argument('--downloads', 
                       default=str(Path.home() / "Downloads"),
                       help='Path to Downloads folder (default: ~/Downloads)')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Show what would be moved without actually moving files')
    parser.add_argument('--execute', 
                       action='store_true',
                       help='Actually move the files (default is dry run)')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Verbose output showing each file operation')
    
    args = parser.parse_args()
    
    # Default to dry run unless --execute is specified
    dry_run = not args.execute
    
    if dry_run and not args.dry_run:
        print("Running in DRY RUN mode by default. Use --execute to actually move files.")
    
    process_downloads_folder(args.downloads, dry_run=dry_run, verbose=args.verbose)

if __name__ == "__main__":
    main()
