#!/bin/bash

export TF_CPP_MIN_LOG_LEVEL=5
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
export GST_DEBUG=python:4


DIR='/home/john/data/maui-data/Karioitahi_09Feb2022/132MSDCF-28mm-f4/DSC0%04d.JPG'
IDX=1013

DIR='/home/john/data/maui-data/karioitahi_13Aug2022/SonyA7C/104MSDCF/DSC0%04d.JPG'
IDX=7274

gst-launch-1.0 multifilesrc location=$DIR index=$IDX caps="image/jpeg,framerate=3/1" ! jpegdec ! videoconvert ! autovideosink