#!/usr/bin/env bash
#
# Usage: ./scripts/clean_tmp.sh
#
# 1. Keeps only the "progress" and "ready" folders in tmp/.
# 2. Removes every other folder in tmp/.
# 3. Within progress/ and ready/, removes all files except for .gitkeep, 
#    and also removes any subdirectories.

set -e

TMP_DIR="./tmp"
KEEP_FOLDERS=("progress" "ready")

# 1. Remove any subdirectory in tmp/ that is not "progress" or "ready".
if [ -d "$TMP_DIR" ]; then
  for dir in "$TMP_DIR"/*; do
    if [ -d "$dir" ]; then
      folder_name=$(basename "$dir")
      # If this folder is not in the list of keepers, remove it.
      keep=false
      for keep_folder in "${KEEP_FOLDERS[@]}"; do
        if [ "$folder_name" = "$keep_folder" ]; then
          keep=true
          break
        fi
      done
      if [ "$keep" = false ]; then
        echo "Removing folder: $dir"
        rm -rf "$dir"
      fi
    fi
  done
fi

# 2. Within the remaining keep folders (progress and ready), remove 
#    everything except for .gitkeep, including subdirectories and mp3s.
for folder_name in "${KEEP_FOLDERS[@]}"; do
  folder_path="$TMP_DIR/$folder_name"
  if [ -d "$folder_path" ]; then
    # Remove any subdirectories
    find "$folder_path" -mindepth 1 -type d -exec rm -rf {} \; 2>/dev/null || true

    # Remove all files except for .gitkeep
    find "$folder_path" -type f ! -name ".gitkeep" -exec rm -f {} \; 2>/dev/null || true
  fi
done

echo "tmp/ has been cleaned. Kept only: tmp/progress/.gitkeep and tmp/ready/.gitkeep"