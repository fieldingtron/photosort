#!/usr/bin/env python3
"""
Script to unzip all takeout*.zip files in the current directory.
"""

import os
import zipfile
import glob
import argparse
from pathlib import Path

def unzip_file(zip_path, extract_to=None):
    """
    Unzip a single file to the specified directory.
    Ignores errors for individual files and continues extracting others.
    
    Args:
        zip_path (str): Path to the zip file
        extract_to (str): Directory to extract to (default: same directory as zip)
    """
    if extract_to is None:
        extract_to = os.path.dirname(zip_path)
    
    print(f"Extracting {zip_path}...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get the total number of files for progress tracking
            total_files = len(zip_ref.namelist())
            print(f"  Found {total_files} files in archive")
            failed_files = []
            # Extract all files
            for member in zip_ref.namelist():
                try:
                    zip_ref.extract(member, extract_to)
                except Exception as e:
                    print(f"    ✗ Failed to extract {member}: {e}")
                    failed_files.append(member)
            if failed_files:
                print(f"  ✗ {len(failed_files)} file(s) failed to extract in {zip_path}")
            else:
                print(f"  ✓ Successfully extracted to {extract_to}")
            
    except zipfile.BadZipFile:
        print(f"  ✗ Error: {zip_path} is not a valid zip file")
        return False
    except Exception as e:
        print(f"  ✗ Error extracting {zip_path}: {str(e)}")
        return False
    
    return True

def find_takeout_zips(directory="."):
    """
    Find all takeout*.zip files in the specified directory.
    
    Args:
        directory (str): Directory to search in
        
    Returns:
        list: List of zip file paths
    """
    pattern = os.path.join(directory, "takeout*.zip")
    zip_files = glob.glob(pattern, recursive=False)
    return sorted(zip_files)

def test_zip_extraction(zip_path, extract_to=None):
    """
    Test if all files in the zip exist in the extraction directory.
    Returns the number of missing files (0 if all exist).
    """
    if extract_to is None:
        extract_to = os.path.dirname(zip_path)
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            missing = []
            for member in zip_ref.namelist():
                out_path = os.path.join(extract_to, member)
                if not os.path.exists(out_path):
                    missing.append(member)
            if missing:
                print(f"  ✗ {zip_path}: {len(missing)} missing files")
                for m in missing[:10]:
                    print(f"    - {m}")
                if len(missing) > 10:
                    print(f"    ...and {len(missing)-10} more")
                return len(missing)
            else:
                print(f"  ✓ {zip_path}: all files present in {extract_to}")
                return 0
    except zipfile.BadZipFile:
        print(f"  ✗ Error: {zip_path} is not a valid zip file")
        return -1
    except Exception as e:
        print(f"  ✗ Error testing {zip_path}: {str(e)}")
        return -1

def main():
    parser = argparse.ArgumentParser(description="Unzip all takeout*.zip files")
    parser.add_argument(
        "--directory", "-d",
        default=".",
        help="Directory to search for zip files (default: current directory)"
    )
    parser.add_argument(
        "--extract-to", "-e",
        help="Directory to extract files to (default: same as zip file location)"
    )
    parser.add_argument(
        "--list-only", "-l",
        action="store_true",
        help="Only list zip files without extracting"
    )
    parser.add_argument(
        "--delete-after", "-r",
        action="store_true",
        help="Delete zip files after successful extraction"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test that all files in each takeout*.zip exist in the extraction directory, without extracting"
    )
    args = parser.parse_args()
    
    # Find all takeout zip files
    zip_files = find_takeout_zips(args.directory)
    
    if not zip_files:
        print("No takeout*.zip files found in the specified directory.")
        return
    
    print(f"Found {len(zip_files)} takeout zip file(s):")
    for zip_file in zip_files:
        print(f"  - {zip_file}")
    
    if args.list_only:
        return
    
    if args.test:
        print("\nTesting extraction completeness...")
        all_ok = True
        total_missing = 0
        zips_to_extract = []
        for zip_file in zip_files:
            missing_count = test_zip_extraction(zip_file, args.extract_to)
            if missing_count > 0:
                all_ok = False
                total_missing += missing_count
                zips_to_extract.append(zip_file)
        print("\nTEST SUMMARY")
        if all_ok:
            print("All zip files have been fully extracted.")
            return
        else:
            print(f"Some zip files are missing extracted files. Total missing files: {total_missing}")
            if zips_to_extract:
                print(f"\nRe-extracting {len(zips_to_extract)} zip file(s) with missing files...")
                for zip_file in zips_to_extract:
                    unzip_file(zip_file, args.extract_to)
                print("\nRe-extraction complete.")
            return
    
    print("\nStarting extraction...")
    
    successful_extractions = []
    failed_extractions = []
    
    for zip_file in zip_files:
        success = unzip_file(zip_file, args.extract_to)
        
        if success:
            successful_extractions.append(zip_file)
        else:
            failed_extractions.append(zip_file)
    
    # Summary
    print(f"\n{'='*50}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*50}")
    print(f"Total files processed: {len(zip_files)}")
    print(f"Successfully extracted: {len(successful_extractions)}")
    print(f"Failed extractions: {len(failed_extractions)}")
    
    if failed_extractions:
        print("\nFailed files:")
        for failed_file in failed_extractions:
            print(f"  - {failed_file}")
    
    # Delete zip files if requested and extraction was successful
    if args.delete_after and successful_extractions:
        print(f"\nDeleting successfully extracted zip files...")
        for zip_file in successful_extractions:
            try:
                os.remove(zip_file)
                print(f"  ✓ Deleted {zip_file}")
            except Exception as e:
                print(f"  ✗ Failed to delete {zip_file}: {str(e)}")

if __name__ == "__main__":
    main()
