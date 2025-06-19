#!/usr/bin/env python3
"""
DNG to HEIC Converter

This script converts DNG (Digital Negative) files to HEIC format.
DNG files are RAW image files that contain unprocessed image data.
HEIC is Apple's efficient image format with excellent compression.
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image
import pillow_heif
from tqdm import tqdm
import rawpy
import numpy as np

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()

def find_dng_files(directory):
    """Find all DNG files in the directory recursively."""
    dng_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.dng'):
                dng_files.append(os.path.join(root, file))
    return dng_files

def convert_dng_to_heic(dng_path, output_dir=None, quality=85, dry_run=False, preserve_structure=True):
    """
    Convert a DNG file to HEIC format.
    
    Args:
        dng_path: Path to the DNG file
        output_dir: Output directory (if None, uses same directory as source)
        quality: HEIC quality (1-100, default 85)
        dry_run: If True, only show what would be done
        preserve_structure: If True, maintains directory structure in output
    """
    dng_path = Path(dng_path)
    
    # Check file size first - DNG files should be much larger than a few bytes
    file_size = dng_path.stat().st_size
    if file_size < 1024:  # Less than 1KB is suspicious for a DNG file
        print(f"Skipping {dng_path.name}: File too small ({file_size} bytes) - likely corrupted or placeholder")
        return False
    
    if output_dir:
        output_dir = Path(output_dir)
        if preserve_structure:
            # Maintain relative directory structure
            rel_path = dng_path.parent.relative_to(Path(dng_path).anchor if dng_path.is_absolute() else Path.cwd())
            output_subdir = output_dir / rel_path
        else:
            output_subdir = output_dir
    else:
        output_subdir = dng_path.parent
    
    # Create output filename
    heic_filename = dng_path.stem + '.heic'
    heic_path = output_subdir / heic_filename
    
    if dry_run:
        print(f"Would convert: {dng_path} -> {heic_path} (size: {file_size/1024/1024:.1f}MB)")
        return True
    
    try:
        # Create output directory if it doesn't exist
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        # Try to read and process the DNG file using rawpy first
        try:
            with rawpy.imread(str(dng_path)) as raw:
                # Process the RAW image with basic settings
                rgb = raw.postprocess(
                    use_camera_wb=True,        # Use camera white balance
                    half_size=False,           # Full resolution
                    no_auto_bright=True,       # Don't auto-brighten
                    output_bps=8,              # 8-bit output (for HEIC compatibility)
                    gamma=(2.222, 4.5),        # Standard sRGB gamma
                    output_color=rawpy.ColorSpace.sRGB,  # sRGB color space
                    user_flip=None,            # Use camera orientation
                    auto_bright_thr=0.01       # Auto brightness threshold
                )
            
            # Convert numpy array to PIL Image
            img = Image.fromarray(rgb)
            
        except Exception as rawpy_error:
            # If rawpy fails, try with PIL directly (for some DNG files that are actually TIFF)
            print(f"Rawpy failed for {dng_path.name}, trying PIL: {rawpy_error}")
            try:
                with Image.open(dng_path) as img:
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
            except Exception as pil_error:
                raise Exception(f"Both rawpy and PIL failed. Rawpy: {rawpy_error}, PIL: {pil_error}")
        
        # Save as HEIC
        img.save(
            heic_path,
            format='HEIF',
            quality=quality,
            optimize=True
        )
        
        print(f"Converted: {dng_path.name} -> {heic_path.name} ({file_size/1024/1024:.1f}MB -> {heic_path.stat().st_size/1024/1024:.1f}MB)")
        return True
        
    except Exception as e:
        print(f"Error converting {dng_path.name}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert DNG files to HEIC format')
    parser.add_argument('input_dir', help='Input directory containing DNG files')
    parser.add_argument('-o', '--output', help='Output directory (default: same as input)')
    parser.add_argument('-q', '--quality', type=int, default=85, 
                       help='HEIC quality (1-100, default: 85)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without actually converting')
    parser.add_argument('--no-preserve-structure', action='store_true',
                       help='Put all converted files in output root (don\'t preserve directory structure)')
    parser.add_argument('--delete-original', action='store_true',
                       help='Delete original DNG files after successful conversion')
    
    args = parser.parse_args()
    
    # Validate input directory
    input_dir = Path(args.input_dir).expanduser()
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)
    
    # Set up output directory
    output_dir = None
    if args.output:
        output_dir = Path(args.output).expanduser()
        if args.dry_run:
            print(f"Output directory: {output_dir}")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all DNG files
    print(f"Scanning for DNG files in: {input_dir}")
    dng_files = find_dng_files(input_dir)
    
    if not dng_files:
        print("No DNG files found.")
        return
    
    print(f"Found {len(dng_files)} DNG files")
    
    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
        print("The following conversions would be performed:")
    
    # Convert files
    successful = 0
    failed = 0
    
    for dng_file in tqdm(dng_files, desc="Converting DNG files"):
        success = convert_dng_to_heic(
            dng_file,
            output_dir=output_dir,
            quality=args.quality,
            dry_run=args.dry_run,
            preserve_structure=not args.no_preserve_structure
        )
        
        if success:
            successful += 1
            # Delete original if requested and not in dry run mode
            if args.delete_original and not args.dry_run:
                try:
                    os.remove(dng_file)
                    print(f"Deleted original: {dng_file}")
                except Exception as e:
                    print(f"Warning: Could not delete {dng_file}: {e}")
        else:
            failed += 1
    
    # Summary
    print(f"\n--- Summary ---")
    print(f"Successful conversions: {successful}")
    if failed > 0:
        print(f"Failed conversions: {failed}")
    
    if args.dry_run:
        print("\nTo perform actual conversion, run without --dry-run flag")

if __name__ == "__main__":
    main()
