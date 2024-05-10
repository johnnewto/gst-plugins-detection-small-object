#!/bin/bash

export TF_CPP_MIN_LOG_LEVEL=5
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
export GST_DEBUG=python:4   # Enable debug python bindings
export GST_DEBUG=3

# Default values
DIR="data/images"
IDX=1013
NUM_BUFFERS=100
OPTION=2

if [ "$(uname -m)" == "x86_64" ]; then
    JPEGDEC="jpegdec"  # if x86
else
    JPEGDEC="nvjpegdec"  # if not x86, e.g., Jetson
fi

while getopts ":o:" opt; do
  case ${opt} in
    o )
      OPTION=$OPTARG
      ;;
    \? )
      echo "Invalid option: -$OPTARG" 1>&2
      echo "Usage: $0 [-o OPTION]"
      exit 1
      ;;
    : )
      echo "Option -$OPTARG requires an argument." 1>&2
      echo "Usage: $0 [-o OPTION]"
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

# Run the selected option
case $OPTION in
  1)
    # Option = videotestsrc + overlay
    gst-launch-1.0 videotestsrc num-buffers=$NUM_BUFFERS ! video/x-raw,width=1920,height=1080 ! videoconvert ! \
        gst_detection_small_obj ! videoconvert ! gst_detection_overlay ! \
        videoconvert ! fpsdisplaysink sync = true
    ;;

  2)
    # Option = multifilesrc plus overlay
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=3/1" ! $JPEGDEC ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! videoscale ! video/x-raw,width=1920,height=1080 ! queue ! \
        gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true
    ;;

  3)
    # Option = tiles plus overlay
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=3/1" ! $JPEGDEC ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! videoscale ! video/x-raw,width=1920,height=1080 ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
        gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true
    ;;

  4)
    # Option = record tiles plus overlay to MP4 using jetson nvv4l2h264enc
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=3/1" ! $JPEGDEC ! queue ! videoconvert !  \
      gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! videoscale ! video/x-raw,width=1920,height=1080 ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
      gst_detection_overlay ! videoconvert ! nvvidconv ! nvv4l2h264enc ! h264parse ! mp4mux ! filesink location=docs/output.mp4
    ;;
  5)
    # Option 3 = fakesink
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=5/1" ! $JPEGDEC ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! fakesink sync=true
    ;;
  *)
    echo "Invalid option: $OPTION" 1>&2
    echo "Usage: $0 [OPTION]"
    exit 1
    ;;
esac
