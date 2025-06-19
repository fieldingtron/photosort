#!/bin/bash

# Simple and Reliable Batch Upload Script for Immich
# Uploads files in batches of 100, verifies, and deletes

set -e  # Exit on any error

# Configuration
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=100
LOG_FILE="batch_upload_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 Batch Upload and Delete Script - $(date)" | tee $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "Batch size: $BATCH_SIZE files" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE

# Count total files first
echo "📊 Counting files..." | tee -a $LOG_FILE
TOTAL_FILES=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \) | wc -l | tr -d ' ')
echo "Found $TOTAL_FILES files to process" | tee -a $LOG_FILE

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "❌ No files found to upload" | tee -a $LOG_FILE
    exit 1
fi

# Get initial server state
INITIAL_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
echo "📊 Initial server file count: $INITIAL_COUNT" | tee -a $LOG_FILE

# Confirm before proceeding
echo "" | tee -a $LOG_FILE
echo "⚠️  WARNING: This will DELETE local files after successful upload!" | tee -a $LOG_FILE
echo "📁 Files to process: $TOTAL_FILES" | tee -a $LOG_FILE
echo "🗂️  Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "🎯 Server: http://YOUR_IMMICH_SERVER:2283" | tee -a $LOG_FILE
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled by user" | tee -a $LOG_FILE
    exit 1
fi

# Initialize counters
BATCH_NUM=1
TOTAL_UPLOADED=0
TOTAL_DELETED=0

# Function to process a batch
process_batch() {
    echo "" | tee -a $LOG_FILE
    echo "📤 Processing Batch $BATCH_NUM..." | tee -a $LOG_FILE
    
    # Create temporary file list for this batch
    BATCH_FILE="batch_${BATCH_NUM}_files.txt"
    find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \) | head -$BATCH_SIZE > "$BATCH_FILE"
    
    # Check if we have files in this batch
    BATCH_COUNT=$(wc -l < "$BATCH_FILE" | tr -d ' ')
    if [ "$BATCH_COUNT" -eq 0 ]; then
        echo "✅ No more files to process" | tee -a $LOG_FILE
        rm -f "$BATCH_FILE"
        return 1
    fi
    
    echo "📋 Batch $BATCH_NUM: $BATCH_COUNT files" | tee -a $LOG_FILE
    
    # Get server count before upload
    BEFORE_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    
    # Upload this batch
    echo "⬆️  Uploading batch $BATCH_NUM..." | tee -a $LOG_FILE
    
    # Build upload command
    UPLOAD_CMD="immich upload"
    while IFS= read -r file; do
        UPLOAD_CMD="$UPLOAD_CMD \"$file\""
    done < "$BATCH_FILE"
    UPLOAD_CMD="$UPLOAD_CMD --album-name \"$ALBUM_NAME\" --concurrency 4"
    
    # Execute upload
    UPLOAD_OUTPUT=$(eval $UPLOAD_CMD 2>&1)
    UPLOAD_STATUS=$?
    
    echo "$UPLOAD_OUTPUT" | tee -a $LOG_FILE
    
    if [ $UPLOAD_STATUS -eq 0 ]; then
        echo "✅ Upload successful" | tee -a $LOG_FILE
        
        # Extract upload stats
        NEW_FILES=$(echo "$UPLOAD_OUTPUT" | grep "Successfully uploaded" | grep -o '[0-9]\+ new assets' | grep -o '[0-9]\+' || echo "0")
        DUPLICATES=$(echo "$UPLOAD_OUTPUT" | grep "duplicates" | grep -o '[0-9]\+ duplicates' | grep -o '[0-9]\+' || echo "0")
        
        echo "📊 New files uploaded: $NEW_FILES" | tee -a $LOG_FILE
        echo "📊 Duplicates found: $DUPLICATES" | tee -a $LOG_FILE
        
        # Wait for server to process
        echo "⏳ Waiting for server processing..." | tee -a $LOG_FILE
        sleep 10
        
        # Verify upload
        AFTER_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
        EXPECTED_COUNT=$((BEFORE_COUNT + NEW_FILES))
        
        echo "📊 Server count: $BEFORE_COUNT → $AFTER_COUNT (expected: $EXPECTED_COUNT)" | tee -a $LOG_FILE
        
        if [ "$AFTER_COUNT" -ge "$EXPECTED_COUNT" ] && [ $((NEW_FILES + DUPLICATES)) -gt 0 ]; then
            echo "✅ Verification passed!" | tee -a $LOG_FILE
            
            # Delete the files
            echo "🗑️  Deleting local files..." | tee -a $LOG_FILE
            DELETED_COUNT=0
            while IFS= read -r file; do
                if [ -f "$file" ]; then
                    if rm "$file"; then
                        echo "  Deleted: $file" >> $LOG_FILE
                        DELETED_COUNT=$((DELETED_COUNT + 1))
                    else
                        echo "  Failed to delete: $file" | tee -a $LOG_FILE
                    fi
                fi
            done < "$BATCH_FILE"
            
            echo "✅ Batch $BATCH_NUM: Deleted $DELETED_COUNT files" | tee -a $LOG_FILE
            TOTAL_UPLOADED=$((TOTAL_UPLOADED + NEW_FILES))
            TOTAL_DELETED=$((TOTAL_DELETED + DELETED_COUNT))
            
        else
            echo "❌ Verification failed - keeping files safe" | tee -a $LOG_FILE
        fi
    else
        echo "❌ Upload failed - keeping files safe" | tee -a $LOG_FILE
    fi
    
    # Clean up
    rm -f "$BATCH_FILE"
    BATCH_NUM=$((BATCH_NUM + 1))
    
    # Show progress
    REMAINING=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \) | wc -l | tr -d ' ')
    echo "📊 Progress: Uploaded $TOTAL_UPLOADED, Deleted $TOTAL_DELETED, Remaining $REMAINING" | tee -a $LOG_FILE
    
    return 0
}

# Main processing loop
echo "" | tee -a $LOG_FILE
echo "🔄 Starting batch processing..." | tee -a $LOG_FILE

while process_batch; do
    echo "⏸️  Pausing 5 seconds before next batch..." | tee -a $LOG_FILE
    sleep 5
done

# Final summary
FINAL_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
REMAINING_FILES=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \) | wc -l | tr -d ' ')

echo "" | tee -a $LOG_FILE
echo "🎉 Processing completed at $(date)" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE
echo "📊 FINAL SUMMARY:" | tee -a $LOG_FILE
echo "  Original files: $TOTAL_FILES" | tee -a $LOG_FILE
echo "  Files uploaded: $TOTAL_UPLOADED" | tee -a $LOG_FILE
echo "  Files deleted: $TOTAL_DELETED" | tee -a $LOG_FILE
echo "  Remaining local files: $REMAINING_FILES" | tee -a $LOG_FILE
echo "  Server files: $INITIAL_COUNT → $FINAL_COUNT" | tee -a $LOG_FILE

echo ""
echo "✨ Check your Immich web interface at: http://YOUR_IMMICH_SERVER:2283"
echo "📁 Look for the album: '$ALBUM_NAME'"
echo "📄 Log saved to: $LOG_FILE"

if [ "$REMAINING_FILES" -gt 0 ]; then
    echo ""
    echo "💡 $REMAINING_FILES files remain - likely due to upload failures"
    echo "   You can re-run this script to process remaining files"
fi
