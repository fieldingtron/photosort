#!/bin/bash

# TEST VERSION - Process just 10 files in batches of 5
ALBUM_NAME="Photo Export 2025"
BATCH_SIZE=5
MAX_FILES=10
LOG_FILE="test_simple_$(date +%Y%m%d_%H%M%S).log"

echo "🧪 TEST: Simple Batch Upload (max $MAX_FILES files)" | tee $LOG_FILE

# Count files for test
TOTAL_FILES=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" \) | head -$MAX_FILES | wc -l | tr -d ' ')
echo "Found $TOTAL_FILES files for test" | tee -a $LOG_FILE

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "❌ No files found" | tee -a $LOG_FILE
    exit 1
fi

echo "⚠️  This will DELETE $TOTAL_FILES local files after upload!"
read -p "Continue with test? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Test cancelled" | tee -a $LOG_FILE
    exit 1
fi

BATCH_NUM=1

while true; do
    echo "" | tee -a $LOG_FILE
    echo "📤 Test Batch $BATCH_NUM" | tee -a $LOG_FILE
    
    # Get files for this batch
    BATCH_FILE="test_batch_${BATCH_NUM}.txt"
    find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" \) | head -$BATCH_SIZE > "$BATCH_FILE"
    
    BATCH_COUNT=$(wc -l < "$BATCH_FILE" | tr -d ' ')
    if [ "$BATCH_COUNT" -eq 0 ]; then
        echo "✅ No more files" | tee -a $LOG_FILE
        rm -f "$BATCH_FILE"
        break
    fi
    
    echo "📋 Processing $BATCH_COUNT files" | tee -a $LOG_FILE
    
    # Get server count before
    BEFORE=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
    
    # Create file list for upload
    FILE_LIST=""
    while IFS= read -r file; do
        FILE_LIST="$FILE_LIST \"$file\""
    done < "$BATCH_FILE"
    
    # Upload
    echo "⬆️  Uploading..." | tee -a $LOG_FILE
    UPLOAD_OUTPUT=$(eval "immich upload $FILE_LIST --album-name \"$ALBUM_NAME\"" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "$UPLOAD_OUTPUT" | tee -a $LOG_FILE
        
        # Wait and verify
        sleep 5
        AFTER=$(immich server-info 2>/dev/null | grep "Total:" | awk '{print $2}' || echo "0")
        
        NEW_FILES=$(echo "$UPLOAD_OUTPUT" | grep "Successfully uploaded" | grep -o '[0-9]\+ new assets' | grep -o '[0-9]\+' || echo "0")
        
        echo "📊 Server: $BEFORE → $AFTER, New: $NEW_FILES" | tee -a $LOG_FILE
        
        if [ "$AFTER" -ge "$BEFORE" ]; then
            echo "✅ Upload verified, deleting files..." | tee -a $LOG_FILE
            
            while IFS= read -r file; do
                if rm "$file"; then
                    echo "  Deleted: $file" | tee -a $LOG_FILE
                fi
            done < "$BATCH_FILE"
            
            echo "✅ Batch $BATCH_NUM complete" | tee -a $LOG_FILE
        else
            echo "❌ Verification failed" | tee -a $LOG_FILE
        fi
    else
        echo "❌ Upload failed: $UPLOAD_OUTPUT" | tee -a $LOG_FILE
    fi
    
    rm -f "$BATCH_FILE"
    BATCH_NUM=$((BATCH_NUM + 1))
    
    # Check remaining
    REMAINING=$(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" \) | wc -l | tr -d ' ')
    echo "📊 Remaining files: $REMAINING" | tee -a $LOG_FILE
    
    if [ "$REMAINING" -eq 0 ]; then
        break
    fi
    
    sleep 3
done

echo "" | tee -a $LOG_FILE
echo "🧪 Test completed! Check $LOG_FILE" | tee -a $LOG_FILE
echo "If successful, run: ./simple_batch_upload.sh"
