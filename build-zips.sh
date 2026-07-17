#!/bin/bash
set -e
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASEDIR"

BITRATE="96k"
MAX_MB=24
STAGE=$(mktemp -d)
trap "rm -rf '$STAGE'" EXIT

echo "Building release zips at ${BITRATE} (max ${MAX_MB}MB each)..."

for dir in Audio/*/; do
  name="$(basename "$dir")"
  count=0
  for f in "$dir"*.mp3; do [ -e "$f" ] && count=$((count+1)); done
  [ "$count" -eq 0 ] && continue

  rm -rf "$STAGE/tracks"
  mkdir -p "$STAGE/tracks"

  for f in "$dir"*.mp3; do
    [ -e "$f" ] || continue
    ffmpeg -y -i "$f" -b:a "$BITRATE" -map_metadata 0 "$STAGE/tracks/$(basename "$f")" -loglevel error
  done

  # Check total size
  total_bytes=$(du -sb "$STAGE/tracks" | cut -f1)
  max_bytes=$((MAX_MB * 1024 * 1024))

  # Remove old zips for this release
  rm -f "Audio/$name.zip" "Audio/$name - Part"*.zip

  if [ "$total_bytes" -le "$max_bytes" ]; then
    (cd "$STAGE/tracks" && zip -j -q "$BASEDIR/Audio/$name.zip" *.mp3)
    size=$(du -h "Audio/$name.zip" | cut -f1)
    echo "  ✓ ${name}.zip (${count} tracks, ${size})"
  else
    # Split into parts that fit under max
    part=1
    partdir="$STAGE/part"
    mkdir -p "$partdir"
    part_bytes=0

    for f in "$STAGE/tracks/"*.mp3; do
      fsize=$(stat -c%s "$f")
      if [ "$part_bytes" -gt 0 ] && [ $((part_bytes + fsize)) -gt "$max_bytes" ]; then
        (cd "$partdir" && zip -j -q "$BASEDIR/Audio/$name - Part $part.zip" *.mp3)
        size=$(du -h "Audio/$name - Part $part.zip" | cut -f1)
        pcount=$(ls "$partdir"/*.mp3 | wc -l)
        echo "  ✓ ${name} - Part ${part}.zip (${pcount} tracks, ${size})"
        rm -f "$partdir/"*.mp3
        part=$((part + 1))
        part_bytes=0
      fi
      cp "$f" "$partdir/"
      part_bytes=$((part_bytes + fsize))
    done

    if [ "$(ls "$partdir"/*.mp3 2>/dev/null | wc -l)" -gt 0 ]; then
      (cd "$partdir" && zip -j -q "$BASEDIR/Audio/$name - Part $part.zip" *.mp3)
      size=$(du -h "Audio/$name - Part $part.zip" | cut -f1)
      pcount=$(ls "$partdir"/*.mp3 | wc -l)
      echo "  ✓ ${name} - Part ${part}.zip (${pcount} tracks, ${size})"
    fi

    rm -rf "$partdir"
  fi
done

echo "Building EPK zip..."
if [ -d "Ash Stu - Electronic Press Kit" ]; then
  rm -rf "$STAGE/epk"
  mkdir -p "$STAGE/epk"

  find "Ash Stu - Electronic Press Kit" -type f ! -name "*.mp3" | while IFS= read -r f; do
    rel="${f#Ash Stu - Electronic Press Kit/}"
    mkdir -p "$STAGE/epk/$(dirname "$rel")"
    cp "$f" "$STAGE/epk/$rel"
  done

  find "Ash Stu - Electronic Press Kit" -type f -name "*.mp3" | while IFS= read -r f; do
    rel="${f#Ash Stu - Electronic Press Kit/}"
    mkdir -p "$STAGE/epk/$(dirname "$rel")"
    ffmpeg -y -i "$f" -b:a "$BITRATE" -map_metadata 0 "$STAGE/epk/$rel" -loglevel error
  done

  rm -f "Ash Stu - Electronic Press Kit.zip"
  (cd "$STAGE/epk" && zip -r -q "$BASEDIR/Ash Stu - Electronic Press Kit.zip" .)
  size=$(du -h "Ash Stu - Electronic Press Kit.zip" | cut -f1)
  echo "  ✓ Ash Stu - Electronic Press Kit.zip (${size})"
fi

echo "Done."
