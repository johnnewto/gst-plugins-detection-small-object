#!/bin/bash

file_path_x86="/home/$USER/.cache/gstreamer-1.0/registry.x86_64.bin"
file_path_aarch64="/home/$USER/.cache/gstreamer-1.0/registry.aarch64.bin"

if [ "$(uname -m)" == "x86_64" ]; then
    if [ -f "$file_path_x86" ]; then
        rm "$file_path_x86"
        echo "Gstreamer cache file for x86 removed successfully."
    else
        echo "File for x86 does not exist."
    fi
elif [ "$(uname -m)" == "aarch64" ]; then
    if [ -f "$file_path_aarch64" ]; then
        rm "$file_path_aarch64"
        echo "Gstreamer cache file for aarch64 removed successfully."
    else
        echo "File for aarch64 does not exist."
    fi
else
    echo "Unsupported platform."
fi

