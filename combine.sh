#!/bin/bash

# Check if a directory is provided
if [ -z "$1" ]; then
    echo "Please provide a directory."
    exit 1
fi

# The directory to process
DIRECTORY=$1

# The output file
OUTPUT_FILE="all_output.txt"

# Clear the output file if it already exists
> "$OUTPUT_FILE"

# Array of file extensions to exclude
EXCLUDE_EXTENSIONS=("png" "yaml" "ttf" "tmx" "otf" "tsx" "txt" "aseprite" "__pycache__" "bk")

# Build the exclude pattern
EXCLUDE_PATTERN=$(printf "|%s" "${EXCLUDE_EXTENSIONS[@]}")
EXCLUDE_PATTERN=${EXCLUDE_PATTERN:1} # remove the leading "|"

# Generate Dir Structuer
tree ./space/ -I '__pycache__' >> "$OUTPUT_FILE"
# Process each file in the directory tree
find "$DIRECTORY" -type f | grep -Ev "($EXCLUDE_PATTERN)" | while read -r file; do
    echo "Processing $file"
    
    # Print the file path to the output file
    echo "File: $file" >> "$OUTPUT_FILE"
    
    # Append the contents of the file to the output file
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "----" >> "$OUTPUT_FILE"
    
    # Optional: Add a separator between files
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

echo "All files have been processed. Output is in $OUTPUT_FILE"
