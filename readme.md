# Project File Documentation

## Python Scripts

- **activate_venv.ps1**: PowerShell script to activate the Python virtual environment and display installed packages.
- **batch_upload.py**: Python version of the batch upload script for Immich. Uploads files in batches, logs progress, and supports concurrency and delays between batches.
- **check_orientations.py**: Python version of the EXIF orientation checker. Prints the orientation of the first 10 images in the current directory.
- **convert_dng_to_heic.py**: Converts DNG (RAW) image files to HEIC format using Pillow, rawpy, and pillow-heif.
- **dng_to_heic.py**: Alternative DNG to HEIC converter with support for batch processing and directory structure preservation.
- **export_all_photos.py**: Exports all photos from the macOS Photos library, deduplicates by file hash, and caches exported ("kept") photos for resumable exports. Skips macOS resource fork files, uses persistent hash cache for speed, and provides robust error handling for file operations.
- **find_similar_images.py**: Batch-computes perceptual hashes for images in a directory, groups visually similar images, and outputs results for further review or deduplication. Designed for efficient large-scale similarity analysis with persistent hash caching.
- **move_images.py**: Recursively moves image files from Downloads to ~/PhotoExport, non-images to ~/NoMatch.
- **photo_test_summary.py**: Prints a summary of photo management tools and capabilities, especially for Windows.
- **requirements_dng.txt**: Python dependencies for DNG/HEIC conversion and image processing.
- **requirements_dng_converter.txt**: Dependencies for DNG to HEIC conversion scripts.
- **restore-exif_from_json.sh**: Restores EXIF metadata to images from Google Takeout JSON files using exiftool and jq.
- **restore_exif.py**: Recursively restores EXIF metadata to images from Google Takeout .json files using piexif and Pillow.
- **rotate_and_upload.py**: Python version of the auto-rotate and upload script. Auto-rotates images based on EXIF, then uploads in batches to Immich.
- **safe_upload_and_delete.py**: Python version of the safe batch upload and delete script. Uploads files in batches, verifies upload, and deletes originals only after verification.
- **setup_immich.py**: Python version of the Immich CLI setup script. Checks for Node.js/npm and installs the Immich CLI.
- **simple_batch_upload.py**: Python version of the simple batch upload and delete script. Uploads files in batches, verifies, and deletes after upload.
- **similiar-fotos.py**: Finds visually similar images using perceptual hashing, displays them side-by-side in an interactive GUI (keep, delete, delete both), and supports robust file deletion, progress bars, and persistent hash caching for efficient repeated runs.
- **sort_photos.py**: Sorts and organizes photos and videos by date, removes duplicates, and maintains a hash database.
- **test_comprehensive_photo_manager.py**: Comprehensive test script for photo sorting, metadata extraction, and organization on Windows.
- **test_image.jpg**: Sample image file for testing scripts.
- **test_photo_tools.py**: Tests alternative photo management tools (Pillow, ExifRead, etc.) on Windows.
- **test_simple.py**: Python version of the test batch upload script. Processes just 10 files in batches of 5, deletes after upload.
- **test_upload.py**: Python version of the test safe batch upload and delete script. Processes only 10 files in batches of 5, deletes after upload.
- **test_windows_photo_manager.py**: Simple photo management test script for Windows, creates and analyzes test photos.
- **unzip_takeout.py**: Unzips all takeout*.zip files in a directory, with options to list, extract, and delete after extraction.
- **upload_batch.py**: Python version of the robust batch upload script. Uploads files in batches, logs progress, and handles errors.

## Other Files

- **.gitignore**: Git ignore rules for the project.
- **README.md**: Project overview and documentation (this file).

## Privacy Notice

This project does not contain any hardcoded personal identifying information (PII) in its source code. However, the scripts process image files, and those files may contain PII in their EXIF metadata (such as GPS location, device information, or timestamps). The scripts only read EXIF date/time fields for sorting and grouping purposes and do not export, log, or display any other EXIF metadata by default.

**If you share or commit sample images, test data, or logs, review those files for sensitive metadata.**

- No user names, emails, or other PII are stored or transmitted by the scripts.
- All processing is local to your machine unless you explicitly upload files to a remote service (e.g., Immich).
- You are responsible for the privacy of your own image files and any data you choose to share.