#!/bin/bash

# Robust batch upload script for Immich
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=50
LOG_FILE="upload_progress.log"
SUCCESS_LOG="uploaded_files.log"
ERROR_LOG="upload_errors.log"

echo "🚀 Starting Immich batch upload at $(date)" | tee $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "Batch size: $BATCH_SIZE files per batch" | tee -a $LOG_FILE

# Initialize counters
TOTAL_UPLOADED=0
TOTAL_FAILED=0
BATCH_NUM=1

# Function to upload a batch of files
upload_batch() {
    local files=("$@")
    local file_count=${#files[@]}
    
    echo "📤 Batch $BATCH_NUM: Uploading $file_count files..." | tee -a $LOG_FILE
    
    if immich upload "${files[@]}" --album-name "$ALBUM_NAME" --concurrency 2 2>>$ERROR_LOG; then
        echo "✅ Batch $BATCH_NUM: Successfully uploaded $file_count files" | tee -a $LOG_FILE
        printf '%s\n' "${files[@]}" >> $SUCCESS_LOG
        TOTAL_UPLOADED=$((TOTAL_UPLOADED + file_count))
    else
        echo "❌ Batch $BATCH_NUM: Failed to upload $file_count files" | tee -a $LOG_FILE
        TOTAL_FAILED=$((TOTAL_FAILED + file_count))
    fi
    
    # Show server stats
    echo "Server status after batch $BATCH_NUM:" | tee -a $LOG_FILE
    immich server-info | grep "Total:" | tee -a $LOG_FILE
    
    BATCH_NUM=$((BATCH_NUM + 1))
}

# Get all image files
echo "📊 Scanning for files..." | tee -a $LOG_FILE
readarray -t ALL_FILES < <(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.mov" -o -iname "*.mp4" \) | head -1000)

TOTAL_FILES=${#ALL_FILES[@]}
echo "Found $TOTAL_FILES files to upload" | tee -a $LOG_FILE

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ No files found to upload" | tee -a $LOG_FILE
    exit 1
fi

# Upload in batches
batch_files=()
for file in "${ALL_FILES[@]}"; do
    batch_files+=("$file")
    
    # When we reach batch size, upload
    if [ ${#batch_files[@]} -eq $BATCH_SIZE ]; then
        upload_batch "${batch_files[@]}"
        batch_files=()
        
        # Small delay between batches
        sleep 3
    fi
done

# Upload remaining files
if [ ${#batch_files[@]} -gt 0 ]; then
    upload_batch "${batch_files[@]}"
fi

# Final summary
echo "" | tee -a $LOG_FILE
echo "🎉 Upload completed at $(date)" | tee -a $LOG_FILE
echo "Summary:" | tee -a $LOG_FILE
echo "  Total files processed: $TOTAL_FILES" | tee -a $LOG_FILE
echo "  Successfully uploaded: $TOTAL_UPLOADED" | tee -a $LOG_FILE
echo "  Failed uploads: $TOTAL_FAILED" | tee -a $LOG_FILE

# Final server check
echo "" | tee -a $LOG_FILE
echo "Final server status:" | tee -a $LOG_FILE
immich server-info | tee -a $LOG_FILE

echo ""
echo "✨ Check your Immich web interface at: http://YOUR_IMMICH_SERVER:2283"
echo "📁 Look for the album: '$ALBUM_NAME'"
echo "📄 Logs saved to: $LOG_FILE, $SUCCESS_LOG, $ERROR_LOG"
