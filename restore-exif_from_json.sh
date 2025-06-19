#!/bin/bash

PHOTO_DIR="$1"

if [ -z "$PHOTO_DIR" ]; then
  echo "Usage: $0 /path/to/GooglePhotosFolder"
  exit 1
fi

cd "$PHOTO_DIR" || exit

shopt -s nullglob
for json_file in *.json; do
    img_file="${json_file%.json}"
    if [[ -f "$img_file" ]]; then
        timestamp=$(jq -r '.photoTakenTime.timestamp' "$json_file")
        datetime=$(date -r "$timestamp" +"%Y:%m:%d %H:%M:%S")

        lat=$(jq -r '.geoData.latitude' "$json_file")
        lon=$(jq -r '.geoData.longitude' "$json_file")

        if [[ "$lat" != "0.0" && "$lon" != "0.0" ]]; then
          lat_ref=$(echo "$lat >= 0" | bc -l | grep -q 1 && echo N || echo S)
          lon_ref=$(echo "$lon >= 0" | bc -l | grep -q 1 && echo E || echo W)
        else
          lat_ref=""
          lon_ref=""
        fi

        echo "Writing EXIF to $img_file"

        exiftool -overwrite_original \
          "-DateTimeOriginal=$datetime" \
          "-CreateDate=$datetime" \
          "-GPSLatitude=$lat" \
          "-GPSLatitudeRef=$lat_ref" \
          "-GPSLongitude=$lon" \
          "-GPSLongitudeRef=$lon_ref" \
          "$img_file"
    fi
done
