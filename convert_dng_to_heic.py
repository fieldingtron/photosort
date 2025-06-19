#!/usr/bin/env python3
"""
DNG to HEIC Converter

This script converts DNG (Digital Negative) RAW files to HEIC format with high quality.
DNG files are typically very large (20-50MB) while HEIC provides excellent compression
with good quality retention (usually 2-5MB).

Requirements:
- pillow-heif (for HEIC support)
- Pillow (PIL)
- rawpy (for DNG reading)

Install with: pip install pillow-heif Pillow rawpy
"""

import os
import sys
import argparse
from pathlib import Path
import rawpy
from PIL import Image
import pillow_heif

# Register HEIF opener with Pillow
pillow_heif.register_heif_opener()


def convert_dng_to_heic(dng_path, output_dir=None, quality=85, dry_run=False):
    """
    Convert a single DNG file to HEIC format.
    
    Args:
        dng_path: Path to the DNG file
        output_dir: Output directory (defaults to same as input)
        quality: HEIC quality (0-100, default 85)
        dry_run: If True, don't actually convert
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        dng_path = Path(dng_path)
        
        # Determine output path
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            heic_path = output_dir / f"{dng_path.stem}.heic"
        else:
            heic_path = dng_path.parent / f"{dng_path.stem}.heic"
        
        # Check if output already exists
        if heic_path.exists():
            print(f"  Skipping {dng_path.name} - HEIC already exists")
            return True
        
        if dry_run:
            print(f"  Would convert {dng_path.name} -> {heic_path.name}")
            return True
        
        print(f"  Converting {dng_path.name} -> {heic_path.name}")
        
        # Read DNG file using rawpy
        with rawpy.imread(str(dng_path)) as raw:
            # Process the RAW data to RGB
            rgb = raw.postprocess(
                use_camera_wb=True,      # Use camera white balance
                half_size=False,         # Full resolution
                no_auto_bright=True,     # Don't auto-brighten
                output_bps=8            # 8-bit output
            )
        
        # Convert to PIL Image
        image = Image.fromarray(rgb)
        
        # Save as HEIC
        image.save(
            str(heic_path),
            format='HEIF',
            quality=quality,
            optimize=True
        )
        
        # Get file sizes for comparison
        original_size = dng_path.stat().st_size / (1024 * 1024)  # MB
        heic_size = heic_path.stat().st_size / (1024 * 1024)     # MB
        compression_ratio = original_size / heic_size if heic_size > 0 else 0
        
        print(f"    ✓ Success: {original_size:.1f}MB -> {heic_size:.1f}MB ({compression_ratio:.1f}x smaller)")
        return True
        
    except Exception as e:
        print(f"    ✗ Error converting {dng_path.name}: {str(e)}")
        return False


def find_dng_files(directory):
    """Find all DNG files in a directory recursively."""
    directory = Path(directory)
    dng_files = []
    
    for dng_file in directory.rglob("*.dng"):
        dng_files.append(dng_file)
    
    # Also check for uppercase extension
    for dng_file in directory.rglob("*.DNG"):
        dng_files.append(dng_file)
    
    return sorted(dng_files)


def convert_directory(input_dir, output_dir=None, quality=85, dry_run=False):
    """
    Convert all DNG files in a directory to HEIC.
    
    Args:
        input_dir: Directory to search for DNG files
        output_dir: Output directory (optional)
        quality: HEIC quality (0-100)
        dry_run: If True, don't actually convert
    
    Returns:
        tuple: (successful_conversions, failed_conversions)
    """
    print(f"Searching for DNG files in: {input_dir}")
    dng_files = find_dng_files(input_dir)
    
    if not dng_files:
        print("No DNG files found!")
        return 0, 0
    
    print(f"Found {len(dng_files)} DNG files")
    
    if dry_run:
        print("\nDRY RUN MODE - No files will be converted")
        print("=" * 50)
    
    successful = 0
    failed = 0
    
    for i, dng_file in enumerate(dng_files, 1):
        print(f"\n[{i}/{len(dng_files)}] Processing: {dng_file.name}")
        
        if convert_dng_to_heic(dng_file, output_dir, quality, dry_run):
            successful += 1
        else:
            failed += 1
    
    return successful, failed


def main():
    parser = argparse.ArgumentParser(
        description="Convert DNG files to HEIC format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert all DNG files in current directory
  python convert_dng_to_heic.py .
  
  # Convert with custom quality and output directory
  python convert_dng_to_heic.py /path/to/dngs --output ~/converted_heic --quality 90
  
  # Dry run to see what would be converted
  python convert_dng_to_heic.py /path/to/dngs --dry-run
        """
    )
    
    parser.add_argument("input_dir", 
                       help="Directory containing DNG files to convert")
    parser.add_argument("--output", "-o", 
                       help="Output directory for HEIC files (default: same as input)")
    parser.add_argument("--quality", "-q", type=int, default=85, 
                       help="HEIC quality 0-100 (default: 85)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without converting")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist!")
        sys.exit(1)
    
    # Validate quality
    if not 0 <= args.quality <= 100:
        print("Error: Quality must be between 0 and 100")
        sys.exit(1)
    
    print("DNG to HEIC Converter")
    print("=" * 30)
    print(f"Input directory: {args.input_dir}")
    if args.output:
        print(f"Output directory: {args.output}")
    print(f"Quality: {args.quality}")
    
    try:
        successful, failed = convert_directory(
            args.input_dir, 
            args.output, 
            args.quality, 
            args.dry_run
        )
        
        print("\n" + "=" * 50)
        print("Conversion Summary:")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {successful + failed}")
        
        if args.dry_run:
            print("\nThis was a dry run. Use without --dry-run to actually convert files.")
        
        if successful > 0:
            print(f"\n✓ DNG files converted to HEIC format!")
            print("HEIC files are typically 5-10x smaller than DNG while maintaining good quality.")
        
    except KeyboardInterrupt:
        print("\n\nConversion cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
