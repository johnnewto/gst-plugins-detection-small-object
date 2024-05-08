#!/bin/bash


export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
export GST_DEBUG=python:4

gst-launch-1.0 videotestsrc num_buffers=100 ! "video/x-raw,format=RGBA, width=1920,height=1080" ! videoconvert !  gstvideocrop left=1500 top=200 bottom=10 right=50 !  videoconvert ! xvimagesink


# DIR='/home/john/data/maui-data/karioitahi_13Aug2022/SonyA7C/104MSDCF/DSC0%04d.JPG'
# IDX=7274
# DIR='/home/john/data/maui-data/Karioitahi_09Feb2022/132MSDCF-28mm-f4/DSC0%04d.JPG'
# DIR='/home/john/data/maui-data/Karioitahi_09Feb2022/132MSDCF-28mm-f4-4000x3000/DSC0%04d.JPG'

# IDX=1013

#  gst-launch-1.0 multifilesrc location="$DIR" start-index=$IDX num-buffers=100 caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert ! \
#     gst_detection_small_obj ! videoconvert ! "video/x-raw,format=RGBA" !  gstvideocrop left=2000 top=00 bottom=1000 right=50 !  videoconvert ! \
#     gst_detection_overlay ! videoconvert ! autovideosink sync = true

