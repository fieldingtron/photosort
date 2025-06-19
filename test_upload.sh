#!/bin/bash

# TEST VERSION - Safe Batch Upload and Delete Script for Immich
# This is a test version that processes only 10 files in batches of 5
# Use this to test the process before running the full script

set -e  # Exit on any error

# Test Configuration
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=5
MAX_FILES=10  # Only process first 10 files for testing
LOG_FILE="test_upload_$(date +%Y%m%d_%H%M%S).log"

echo "🧪 TEST MODE: Safe Batch Upload with Verification" | tee $LOG_FILE
echo "Will process only first $MAX_FILES files in batches of $BATCH_SIZE" | tee -a $LOG_FILE
echo "Album: $ALBUM_NAME" | tee -a $LOG_FILE
echo "===========================================" | tee -a $LOG_FILE

# Get test files
ALL_FILES=()
count=0
for file in $(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" \)); do
    if [ $count -lt $MAX_FILES ]; then
        ALL_FILES+=("$file")
        count=$((count + 1))
    else
        break
    fi
done

TOTAL_FILES=${#ALL_FILES[@]}
echo "Found $TOTAL_FILES files for testing" | tee -a $LOG_FILE

if [ $TOTAL_FILES -eq 0 ]; then
    echo "❌ No files found for testing" | tee -a $LOG_FILE
    exit 1
fi

# Show files that will be processed
echo "📋 Files that will be processed:" | tee -a $LOG_FILE
printf '%s\n' "${ALL_FILES[@]}" | tee -a $LOG_FILE

echo ""
echo "⚠️  This will DELETE these $TOTAL_FILES local files after successful upload!"
read -p "Continue with test? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Test cancelled by user" | tee -a $LOG_FILE
    exit 1
fi

# Simple upload and verify function for testing
test_batch() {
    local files=("$@")
    local file_count=${#files[@]}
    
    echo "📤 Testing batch: $file_count files" | tee -a $LOG_FILE
    
    # Get before count
    local before_count=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    
    # Upload
    local upload_output=$(immich upload "${files[@]}" --album-name "$ALBUM_NAME" --concurrency 2 2>&1)
    local upload_status=$?
    
    echo "$upload_output" | tee -a $LOG_FILE
    
    if [ $upload_status -eq 0 ]; then
        echo "✅ Upload command successful" | tee -a $LOG_FILE
        
        # Extract actual number of uploaded files from output
        local new_files=$(echo "$upload_output" | grep "Successfully uploaded" | grep -o '[0-9]\+ new assets' | grep -o '[0-9]\+' || echo "0")
        echo "📊 New files uploaded: $new_files" | tee -a $LOG_FILE
        
        # Wait and verify
        sleep 5
        local after_count=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
        local expected=$((before_count + new_files))
        
        echo "📊 Before: $before_count, Expected: $expected, After: $after_count" | tee -a $LOG_FILE
        
        if [[ "$after_count" -ge "$expected" ]] && [[ "$new_files" -gt 0 || "$file_count" -eq $(echo "$upload_output" | grep "duplicates" | grep -o '[0-9]\+ duplicates' | grep -o '[0-9]\+' || echo "0") ]]; then
            echo "✅ Verification passed!" | tee -a $LOG_FILE
            
            # Delete files
            echo "🗑️  Deleting files..." | tee -a $LOG_FILE
            for file in "${files[@]}"; do
                if rm "$file"; then
                    echo "  Deleted: $file" | tee -a $LOG_FILE
                fi
            done
            echo "✅ Test batch complete!" | tee -a $LOG_FILE
            return 0
        else
            echo "❌ Verification failed - keeping files safe" | tee -a $LOG_FILE
            return 1
        fi
    else
        echo "❌ Upload failed" | tee -a $LOG_FILE
        return 1
    fi
}

# Process test files
batch_files=()
for file in "${ALL_FILES[@]}"; do
    batch_files+=("$file")
    
    if [ ${#batch_files[@]} -eq $BATCH_SIZE ]; then
        test_batch "${batch_files[@]}"
        batch_files=()
        sleep 3
    fi
done

# Process remaining files
if [ ${#batch_files[@]} -gt 0 ]; then
    test_batch "${batch_files[@]}"
fi

echo ""
echo "🧪 Test completed! Check results in $LOG_FILE"
echo "If everything looks good, run: ./safe_upload_and_delete.sh"
