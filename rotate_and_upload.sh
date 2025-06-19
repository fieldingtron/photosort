#!/bin/bash

# Auto-rotate and Upload Script for Immich
# This script auto-rotates images based on EXIF data, then uploads in batches

set -e

# Configuration
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=100
LOG_FILE="rotate_upload_$(date +%Y%m%d_%H%M%S).log"
ROTATION_LOG="rotated_files_$(date +%Y%m%d_%H%M%S).log"
SUCCESS_LOG="uploaded_files_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="errors_$(date +%Y%m%d_%H%M%S).log"

# Counters
TOTAL_PROCESSED=0
TOTAL_ROTATED=0
TOTAL_UPLOADED=0
TOTAL_DELETED=0
BATCH_NUM=1

echo "🔄 Auto-Rotate and Upload Script Started at $(date)" | tee $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "Batch size: $BATCH_SIZE files" | tee -a $LOG_FILE
echo "Process: Rotate → Upload → Verify → Delete" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE

# Check if exiftool is available
if ! command -v exiftool &> /dev/null; then
    echo "❌ exiftool not found. Installing..." | tee -a $LOG_FILE
    if command -v brew &> /dev/null; then
        brew install exiftool
    else
        echo "❌ Please install exiftool manually: brew install exiftool" | tee -a $LOG_FILE
        exit 1
    fi
fi

# Check if ImageMagick is available for rotation
if ! command -v magick &> /dev/null && ! command -v convert &> /dev/null; then
    echo "❌ ImageMagick not found. Installing..." | tee -a $LOG_FILE
    if command -v brew &> /dev/null; then
        brew install imagemagick
    else
        echo "❌ Please install ImageMagick manually: brew install imagemagick" | tee -a $LOG_FILE
        exit 1
    fi
fi

# Function to get image orientation
get_orientation() {
    local file="$1"
    local orientation=$(exiftool -Orientation -n -S "$file" 2>/dev/null | cut -d' ' -f2)
    echo "${orientation:-1}"
}

# Function to auto-rotate image based on EXIF orientation
auto_rotate_image() {
    local file="$1"
    local orientation=$(get_orientation "$file")
    local rotated=false
    
    case $orientation in
        1)
            # Normal - no rotation needed
            echo "  $file: No rotation needed (orientation: $orientation)" >> $ROTATION_LOG
            ;;
        2)
            # Flip horizontal
            if magick "$file" -flop "$file" 2>/dev/null || convert "$file" -flop "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Flipped horizontal (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        3)
            # Rotate 180°
            if magick "$file" -rotate 180 "$file" 2>/dev/null || convert "$file" -rotate 180 "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Rotated 180° (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        4)
            # Flip vertical
            if magick "$file" -flip "$file" 2>/dev/null || convert "$file" -flip "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Flipped vertical (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        5)
            # Rotate 90° CCW and flip horizontal
            if magick "$file" -rotate -90 -flop "$file" 2>/dev/null || convert "$file" -rotate -90 -flop "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Rotated 90° CCW + flipped (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        6)
            # Rotate 90° CW
            if magick "$file" -rotate 90 "$file" 2>/dev/null || convert "$file" -rotate 90 "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Rotated 90° CW (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        7)
            # Rotate 90° CW and flip horizontal
            if magick "$file" -rotate 90 -flop "$file" 2>/dev/null || convert "$file" -rotate 90 -flop "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Rotated 90° CW + flipped (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        8)
            # Rotate 90° CCW
            if magick "$file" -rotate -90 "$file" 2>/dev/null || convert "$file" -rotate -90 "$file" 2>/dev/null; then
                rotated=true
                echo "  $file: Rotated 90° CCW (orientation: $orientation)" >> $ROTATION_LOG
            fi
            ;;
        *)
            echo "  $file: Unknown orientation ($orientation), skipping rotation" >> $ROTATION_LOG
            ;;
    esac
    
    # Reset EXIF orientation to 1 (normal) after rotation
    if $rotated; then
        exiftool -Orientation=1 -overwrite_original "$file" 2>/dev/null || true
        return 0
    else
        return 1
    fi
}

# Function to process (rotate) a batch of images
process_batch() {
    local files=("$@")
    local file_count=${#files[@]}
    local rotated_count=0
    
    echo "🔄 Batch $BATCH_NUM: Processing $file_count files..." | tee -a $LOG_FILE
    
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            # Only process image files (skip videos)
            file_lower=$(echo "$file" | tr '[:upper:]' '[:lower:]')
            case "$file_lower" in
                *.jpg|*.jpeg|*.png|*.tiff|*.tif|*.heic|*.heif)
                    if auto_rotate_image "$file"; then
                        rotated_count=$((rotated_count + 1))
                    fi
                    ;;
                *)
                    echo "  $file: Skipping rotation (not an image)" >> $ROTATION_LOG
                    ;;
            esac
        fi
    done
    
    echo "🔄 Batch $BATCH_NUM: Rotated $rotated_count/$file_count files" | tee -a $LOG_FILE
    TOTAL_ROTATED=$((TOTAL_ROTATED + rotated_count))
}

# Function to upload and verify batch
upload_batch() {
    local files=("$@")
    local file_count=${#files[@]}
    
    echo "📤 Batch $BATCH_NUM: Uploading $file_count files..." | tee -a $LOG_FILE
    
    # Get server count before upload
    local before_count=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    
    # Upload files
    local upload_output=$(immich upload "${files[@]}" --album-name "$ALBUM_NAME" --concurrency 4 2>&1)
    local upload_status=$?
    
    if [ $upload_status -eq 0 ]; then
        echo "✅ Upload completed" | tee -a $LOG_FILE
        
        # Extract upload statistics
        local new_files=$(echo "$upload_output" | grep "Successfully uploaded" | grep -o '[0-9]\+ new assets' | grep -o '[0-9]\+' || echo "0")
        local duplicates=$(echo "$upload_output" | grep "duplicates" | grep -o '[0-9]\+ duplicates' | grep -o '[0-9]\+' || echo "0")
        
        echo "  New files: $new_files, Duplicates: $duplicates" | tee -a $LOG_FILE
        
        # Verify upload
        sleep 5
        local after_count=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
        local expected=$((before_count + new_files))
        
        if [[ "$after_count" -ge "$expected" ]]; then
            echo "✅ Verification passed: $before_count → $after_count files" | tee -a $LOG_FILE
            
            # Log successful uploads
            printf '%s\n' "${files[@]}" >> $SUCCESS_LOG
            TOTAL_UPLOADED=$((TOTAL_UPLOADED + file_count))
            
            # Delete files after successful upload
            echo "🗑️  Deleting local files..." | tee -a $LOG_FILE
            local deleted_count=0
            for file in "${files[@]}"; do
                if [[ -f "$file" ]] && rm "$file" 2>/dev/null; then
                    deleted_count=$((deleted_count + 1))
                fi
            done
            
            echo "🗑️  Deleted $deleted_count files" | tee -a $LOG_FILE
            TOTAL_DELETED=$((TOTAL_DELETED + deleted_count))
            
            return 0
        else
            echo "❌ Verification failed: expected $expected, got $after_count" | tee -a $LOG_FILE
            return 1
        fi
    else
        echo "❌ Upload failed" | tee -a $LOG_FILE
        echo "$upload_output" >> $ERROR_LOG
        return 1
    fi
}

# Get all files
echo "📊 Scanning for media files..." | tee -a $LOG_FILE
ALL_FILES=()
for file in $(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.tiff" -o -iname "*.tif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \)); do
    ALL_FILES+=("$file")
done

TOTAL_FILES=${#ALL_FILES[@]}
echo "Found $TOTAL_FILES files to process" | tee -a $LOG_FILE

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ No files found" | tee -a $LOG_FILE
    exit 1
fi

# Get initial server state
INITIAL_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
echo "📊 Initial server files: $INITIAL_COUNT" | tee -a $LOG_FILE

# Confirm before proceeding
echo ""
echo "⚠️  This will:"
echo "   1. Auto-rotate images based on EXIF orientation"
echo "   2. Upload files to Immich in batches of $BATCH_SIZE"
echo "   3. DELETE local files after successful upload"
echo ""
echo "📁 Files to process: $TOTAL_FILES"
echo "🗂️  Album: $ALBUM_NAME"
echo "🎯 Server: http://YOUR_IMMICH_SERVER:2283"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled" | tee -a $LOG_FILE
    exit 1
fi

# Process files in batches
echo ""
echo "🚀 Starting batch processing..." | tee -a $LOG_FILE

batch_files=()
for file in "${ALL_FILES[@]}"; do
    batch_files+=("$file")
    
    if [ ${#batch_files[@]} -eq $BATCH_SIZE ]; then
        echo ""
        echo "==================== BATCH $BATCH_NUM ====================" | tee -a $LOG_FILE
        
        # Process (rotate) the batch
        process_batch "${batch_files[@]}"
        
        # Upload the batch
        if upload_batch "${batch_files[@]}"; then
            echo "✅ Batch $BATCH_NUM: Complete!" | tee -a $LOG_FILE
        else
            echo "❌ Batch $BATCH_NUM: Failed - keeping files" | tee -a $LOG_FILE
        fi
        
        TOTAL_PROCESSED=$((TOTAL_PROCESSED + ${#batch_files[@]}))
        batch_files=()
        BATCH_NUM=$((BATCH_NUM + 1))
        
        # Progress update
        echo "📊 Progress: $TOTAL_PROCESSED/$TOTAL_FILES files processed" | tee -a $LOG_FILE
        
        # Pause between batches
        echo "⏸️  Pausing 10 seconds..." | tee -a $LOG_FILE
        sleep 10
    fi
done

# Process remaining files
if [ ${#batch_files[@]} -gt 0 ]; then
    echo ""
    echo "==================== BATCH $BATCH_NUM (Final) ====================" | tee -a $LOG_FILE
    
    process_batch "${batch_files[@]}"
    upload_batch "${batch_files[@]}"
    
    TOTAL_PROCESSED=$((TOTAL_PROCESSED + ${#batch_files[@]}))
fi

# Final summary
FINAL_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")

echo ""
echo "🎉 Processing completed at $(date)" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE
echo "📊 FINAL SUMMARY:" | tee -a $LOG_FILE
echo "  Files processed: $TOTAL_PROCESSED" | tee -a $LOG_FILE
echo "  Images rotated: $TOTAL_ROTATED" | tee -a $LOG_FILE
echo "  Files uploaded: $TOTAL_UPLOADED" | tee -a $LOG_FILE
echo "  Files deleted: $TOTAL_DELETED" | tee -a $LOG_FILE
echo "  Server files: $INITIAL_COUNT → $FINAL_COUNT" | tee -a $LOG_FILE

# Check remaining files
REMAINING=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" \) | wc -l)
echo "  Remaining files: $REMAINING" | tee -a $LOG_FILE

echo ""
echo "📄 Log files:"
echo "  Main: $LOG_FILE"
echo "  Rotations: $ROTATION_LOG"
echo "  Uploads: $SUCCESS_LOG"
echo "  Errors: $ERROR_LOG"

echo ""
echo "✨ Check your Immich at: http://YOUR_IMMICH_SERVER:2283"
