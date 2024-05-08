#!/bin/bash

file_path="/home/john/.cache/gstreamer-1.0/registry.x86_64.bin"

if [ -f "$file_path" ]; then
    rm "$file_path"
    echo "Gstreamer cache file removed successfully."
else
    echo "File does not exist."
fi

