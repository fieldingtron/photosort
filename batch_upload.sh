#!/bin/bash

# Batch upload script for Immich
# This script uploads files in batches to avoid overwhelming the system

ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=100
LOG_FILE="upload_log.txt"

echo "🚀 Starting batch upload to Immich..." | tee $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "Batch size: $BATCH_SIZE files" | tee -a $LOG_FILE
echo "$(date): Starting upload" | tee -a $LOG_FILE

# Count total files
TOTAL_FILES=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.mov" -o -iname "*.mp4" \) | wc -l)
echo "Total files to upload: $TOTAL_FILES" | tee -a $LOG_FILE

# Upload in batches
UPLOADED=0
BATCH_NUM=1

# Create temporary file list
TEMP_FILE=$(mktemp)
find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.mov" -o -iname "*.mp4" \) > $TEMP_FILE

while IFS= read -r file; do
    echo "$file" >> "batch_${BATCH_NUM}.txt"
    
    # Check if we've reached batch size or end of files
    if (( $(wc -l < "batch_${BATCH_NUM}.txt") >= BATCH_SIZE )) || [[ $(wc -l < $TEMP_FILE) -eq $(( UPLOADED + $(wc -l < "batch_${BATCH_NUM}.txt") )) ]]; then
        echo "📤 Uploading batch $BATCH_NUM ($(wc -l < "batch_${BATCH_NUM}.txt") files)..." | tee -a $LOG_FILE
        
        # Upload this batch
        if immich upload $(cat "batch_${BATCH_NUM}.txt" | tr '\n' ' ') --album-name "$ALBUM_NAME" --concurrency 2; then
            UPLOADED_BATCH=$(wc -l < "batch_${BATCH_NUM}.txt")
            UPLOADED=$((UPLOADED + UPLOADED_BATCH))
            echo "✅ Batch $BATCH_NUM completed ($UPLOADED_BATCH files)" | tee -a $LOG_FILE
        else
            echo "❌ Batch $BATCH_NUM failed" | tee -a $LOG_FILE
        fi
        
        # Clean up batch file
        rm "batch_${BATCH_NUM}.txt"
        
        # Increment batch number
        BATCH_NUM=$((BATCH_NUM + 1))
        
        # Small delay between batches
        sleep 2
    fi
done < $TEMP_FILE

# Clean up
rm $TEMP_FILE

echo "🎉 Upload completed!" | tee -a $LOG_FILE
echo "Files uploaded: $UPLOADED / $TOTAL_FILES" | tee -a $LOG_FILE
echo "$(date): Upload finished" | tee -a $LOG_FILE
