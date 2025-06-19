#!/bin/bash

# Test rotation script - check orientation of first 10 images

echo "🔍 Checking EXIF orientation of first 10 images..."
echo "==========================================="

count=0
for file in $(find . -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.heic" \)); do
    if [ $count -lt 10 ]; then
        orientation=$(exiftool -Orientation -n -S "$file" 2>/dev/null | cut -d' ' -f2)
        orientation=${orientation:-1}
        
        case $orientation in
            1) rotation_needed="None (Normal)" ;;
            2) rotation_needed="Flip horizontal" ;;
            3) rotation_needed="Rotate 180°" ;;
            4) rotation_needed="Flip vertical" ;;
            5) rotation_needed="Rotate 90° CCW + flip" ;;
            6) rotation_needed="Rotate 90° CW" ;;
            7) rotation_needed="Rotate 90° CW + flip" ;;
            8) rotation_needed="Rotate 90° CCW" ;;
            *) rotation_needed="Unknown ($orientation)" ;;
        esac
        
        echo "$file: Orientation $orientation - $rotation_needed"
        count=$((count + 1))
    fi
done

echo ""
echo "Ready to run: ./rotate_and_upload.sh"
