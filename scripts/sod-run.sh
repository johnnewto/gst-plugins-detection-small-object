#!/bin/bash

export TF_CPP_MIN_LOG_LEVEL=5
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
export GST_DEBUG=python:4


# gst-launch-1.0 videotestsrc num-buffers=100 ! video/x-raw,width=1920,height=1080 ! videoconvert ! \
#     gst_detection_small_obj config=data/small_object_api_cfg.yml ! videoconvert ! gst_detection_overlay ! \
#     videoconvert ! autovideosink

# videoconvert ! videoscale ! video/x-raw,width=1280,height=960 ! x264enc ! mp4mux ! filesink location="output.mp4"
# /maui-data/karioitahi_13Aug2022/PhantomDrone/DJI_0087.MP4


 gst-launch-1.0 multifilesrc location="data/images/DSC0%04d.JPG" start-index=1013 num-buffers=100 caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
    gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
    gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true


#  gst-launch-1.0 multifilesrc location="$DIR" start-index=$IDX num-buffers=100  caps="image/jpeg,framerate=3/1" ! \
#     jpegparse ! jpegdec !  \
#     videoconvert ! autovideosink sync=true

# gst-launch-1.0 imagesequencesrc location=image-%05d.jpg start-index=1 stop-index=50 framerate=24/1 ! decodebin ! videoconvert ! autovideosink

# videoconvert ! videoscale ! videorate ! "video/x-raw,width=4000,height=3000" 