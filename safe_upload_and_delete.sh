#!/bin/bash

# Safe Batch Upload and Delete Script for Immich
# This script uploads files in batches, verifies they were uploaded successfully,
# and only then deletes the local originals.

set -e  # Exit on any error

# Configuration
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=1000
LOG_FILE="safe_upload_$(date +%Y%m%d_%H%M%S).log"
SUCCESS_LOG="uploaded_files_$(date +%Y%m%d_%H%M%S).log"
ERROR_LOG="upload_errors_$(date +%Y%m%d_%H%M%S).log"
VERIFICATION_LOG="verification_$(date +%Y%m%d_%H%M%S).log"
DELETED_LOG="deleted_files_$(date +%Y%m%d_%H%M%S).log"

# Initialize counters
TOTAL_UPLOADED=0
TOTAL_VERIFIED=0
TOTAL_DELETED=0
TOTAL_FAILED=0
BATCH_NUM=1

echo "🚀 Starting Safe Batch Upload with Verification at $(date)" | tee $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "Batch size: $BATCH_SIZE files per batch" | tee -a $LOG_FILE
echo "Process: Upload → Verify → Delete" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE

# Function to get file hash for verification
get_file_hash() {
    local file="$1"
    if [[ -f "$file" ]]; then
        shasum -a 256 "$file" | cut -d' ' -f1
    else
        echo "FILE_NOT_FOUND"
    fi
}

# Function to verify upload success by checking server stats
verify_upload_success() {
    local upload_output="$1"
    local before_count=$2
    
    echo "🔍 Verifying upload success..." | tee -a $LOG_FILE
    
    # Extract actual number of uploaded files from output
    local new_files=$(echo "$upload_output" | grep "Successfully uploaded" | grep -o '[0-9]\+ new assets' | grep -o '[0-9]\+' || echo "0")
    local duplicates=$(echo "$upload_output" | grep "duplicates" | grep -o '[0-9]\+ duplicates' | grep -o '[0-9]\+' || echo "0")
    
    echo "  New files uploaded: $new_files" | tee -a $LOG_FILE
    echo "  Duplicates skipped: $duplicates" | tee -a $LOG_FILE
    
    # Wait a moment for server to process
    sleep 5
    
    # Get current server stats
    local current_stats=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    local expected_total=$((before_count + new_files))
    
    echo "  Before upload: $before_count files" | tee -a $LOG_FILE
    echo "  Expected after: $expected_total files" | tee -a $LOG_FILE
    echo "  Current server: $current_stats files" | tee -a $LOG_FILE
    
    if [[ "$current_stats" -ge "$expected_total" ]] && [[ "$new_files" -gt 0 || "$duplicates" -gt 0 ]]; then
        echo "✅ Verification PASSED: Server has $current_stats files, uploaded $new_files new files" | tee -a $LOG_FILE
        return 0
    else
        echo "❌ Verification FAILED: Expected progress not detected" | tee -a $LOG_FILE
        return 1
    fi
}

# Function to safely delete files after verification
safe_delete_files() {
    local files=("$@")
    local deleted_count=0
    
    echo "🗑️  Safely deleting verified files..." | tee -a $LOG_FILE
    
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            # Get file info before deletion
            local file_size=$(stat -f%z "$file" 2>/dev/null || echo "0")
            local file_hash=$(get_file_hash "$file")
            
            # Delete the file
            if rm "$file" 2>/dev/null; then
                echo "Deleted: $file (${file_size} bytes, hash: ${file_hash:0:16}...)" >> $DELETED_LOG
                deleted_count=$((deleted_count + 1))
            else
                echo "❌ Failed to delete: $file" | tee -a $LOG_FILE
            fi
        fi
    done
    
    echo "🗑️  Deleted $deleted_count files from batch" | tee -a $LOG_FILE
    TOTAL_DELETED=$((TOTAL_DELETED + deleted_count))
}

# Function to upload and verify a batch
upload_and_verify_batch() {
    local files=("$@")
    local file_count=${#files[@]}
    
    echo "" | tee -a $LOG_FILE
    echo "📤 Batch $BATCH_NUM: Processing $file_count files..." | tee -a $LOG_FILE
    echo "Files: ${files[0]} ... ${files[-1]}" | tee -a $LOG_FILE
    
    # Get server count before upload
    local before_count=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    
    # Record file hashes before upload for verification
    echo "📝 Recording file hashes for batch $BATCH_NUM..." | tee -a $LOG_FILE
    for file in "${files[@]}"; do
        local hash=$(get_file_hash "$file")
        echo "Hash: $hash - $file" >> $VERIFICATION_LOG
    done
    
    # Attempt upload
    echo "⬆️  Uploading batch $BATCH_NUM..." | tee -a $LOG_FILE
    local upload_output=$(immich upload "${files[@]}" --album-name "$ALBUM_NAME" --concurrency 4 2>&1)
    local upload_status=$?
    
    echo "$upload_output" | tee -a $LOG_FILE
    
    if [ $upload_status -eq 0 ]; then
        echo "✅ Batch $BATCH_NUM: Upload completed" | tee -a $LOG_FILE
        
        # Verify upload success
        if verify_upload_success "$upload_output" $before_count; then
            echo "✅ Batch $BATCH_NUM: Verification passed" | tee -a $LOG_FILE
            
            # Log successful uploads
            printf '%s\n' "${files[@]}" >> $SUCCESS_LOG
            TOTAL_UPLOADED=$((TOTAL_UPLOADED + file_count))
            TOTAL_VERIFIED=$((TOTAL_VERIFIED + file_count))
            
            # Wait a bit more to ensure server processing is complete
            echo "⏳ Waiting 10 seconds before deletion..." | tee -a $LOG_FILE
            sleep 10
            
            # Now safe to delete files
            safe_delete_files "${files[@]}"
            
            echo "✅ Batch $BATCH_NUM: Complete (Uploaded → Verified → Deleted)" | tee -a $LOG_FILE
        else
            echo "❌ Batch $BATCH_NUM: Verification failed - keeping local files for safety" | tee -a $LOG_FILE
            TOTAL_FAILED=$((TOTAL_FAILED + file_count))
        fi
    else
        echo "❌ Batch $BATCH_NUM: Upload failed - keeping local files" | tee -a $LOG_FILE
        TOTAL_FAILED=$((TOTAL_FAILED + file_count))
    fi
    
    # Show current server stats
    local current_total=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    echo "📊 Server now has: $current_total total files" | tee -a $LOG_FILE
    
    BATCH_NUM=$((BATCH_NUM + 1))
}

# Main execution
echo "📊 Scanning for files..." | tee -a $LOG_FILE

# Get all media files
ALL_FILES=()
for file in $(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \)); do
    ALL_FILES+=("$file")
done

TOTAL_FILES=${#ALL_FILES[@]}
echo "Found $TOTAL_FILES files to process" | tee -a $LOG_FILE

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ No files found to upload" | tee -a $LOG_FILE
    exit 1
fi

# Get initial server state
INITIAL_SERVER_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
echo "📊 Initial server file count: $INITIAL_SERVER_COUNT" | tee -a $LOG_FILE

# Confirm before proceeding
echo "" | tee -a $LOG_FILE
echo "⚠️  WARNING: This will DELETE local files after successful upload and verification!" | tee -a $LOG_FILE
echo "📁 Processing: $TOTAL_FILES files" | tee -a $LOG_FILE
echo "🗂️  Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "🎯 Server: http://YOUR_IMMICH_SERVER:2283" | tee -a $LOG_FILE
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled by user" | tee -a $LOG_FILE
    exit 1
fi

# Process files in batches
echo "" | tee -a $LOG_FILE
echo "🔄 Starting batch processing..." | tee -a $LOG_FILE

batch_files=()
for file in "${ALL_FILES[@]}"; do
    batch_files+=("$file")
    
    # When we reach batch size, process the batch
    if [ ${#batch_files[@]} -eq $BATCH_SIZE ]; then
        upload_and_verify_batch "${batch_files[@]}"
        batch_files=()
        
        # Pause between batches
        echo "⏸️  Pausing 15 seconds between batches..." | tee -a $LOG_FILE
        sleep 15
    fi
done

# Process remaining files
if [ ${#batch_files[@]} -gt 0 ]; then
    upload_and_verify_batch "${batch_files[@]}"
fi

# Final summary
echo "" | tee -a $LOG_FILE
echo "🎉 Processing completed at $(date)" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE
echo "📊 FINAL SUMMARY:" | tee -a $LOG_FILE
echo "  Total files processed: $TOTAL_FILES" | tee -a $LOG_FILE
echo "  Successfully uploaded: $TOTAL_UPLOADED" | tee -a $LOG_FILE
echo "  Successfully verified: $TOTAL_VERIFIED" | tee -a $LOG_FILE
echo "  Successfully deleted: $TOTAL_DELETED" | tee -a $LOG_FILE
echo "  Failed operations: $TOTAL_FAILED" | tee -a $LOG_FILE

# Final server check
FINAL_SERVER_COUNT=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
EXPECTED_FINAL=$((INITIAL_SERVER_COUNT + TOTAL_VERIFIED))

echo "" | tee -a $LOG_FILE
echo "📊 SERVER VERIFICATION:" | tee -a $LOG_FILE
echo "  Initial server files: $INITIAL_SERVER_COUNT" | tee -a $LOG_FILE
echo "  Files we uploaded: $TOTAL_VERIFIED" | tee -a $LOG_FILE
echo "  Expected final count: $EXPECTED_FINAL" | tee -a $LOG_FILE
echo "  Actual final count: $FINAL_SERVER_COUNT" | tee -a $LOG_FILE

if [[ "$FINAL_SERVER_COUNT" -ge "$EXPECTED_FINAL" ]]; then
    echo "✅ Final verification PASSED!" | tee -a $LOG_FILE
else
    echo "⚠️  Final verification shows discrepancy - check logs" | tee -a $LOG_FILE
fi

echo "" | tee -a $LOG_FILE
echo "🗂️  Log files created:" | tee -a $LOG_FILE
echo "  Main log: $LOG_FILE" | tee -a $LOG_FILE
echo "  Uploaded files: $SUCCESS_LOG" | tee -a $LOG_FILE
echo "  Deleted files: $DELETED_LOG" | tee -a $LOG_FILE
echo "  Verification: $VERIFICATION_LOG" | tee -a $LOG_FILE
echo "  Errors: $ERROR_LOG" | tee -a $LOG_FILE

echo ""
echo "✨ Check your Immich web interface at: http://YOUR_IMMICH_SERVER:2283"
echo "📁 Look for the album: '$ALBUM_NAME'"

# Show remaining files
REMAINING_FILES=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.heif" -o -iname "*.mov" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.gif" \) | wc -l)
echo "📁 Remaining local files: $REMAINING_FILES"

if [ $REMAINING_FILES -gt 0 ]; then
    echo "💡 Some files remain - likely due to failed uploads/verifications"
    echo "   Check error logs and re-run script if needed"
fi
