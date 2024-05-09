#!/bin/bash

# export TF_CPP_MIN_LOG_LEVEL=5
# export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
# export GST_DEBUG=python:4

# # oprion 1  = overlay
# gst-launch-1.0 videotestsrc num-buffers=100 ! video/x-raw,width=1920,height=1080 ! videoconvert ! \
#     gst_detection_small_obj ! videoconvert ! gst_detection_overlay ! \
#     videoconvert ! fpsdisplaysink sync = true

# # oprion 2  = tiles  plus overlay
#  gst-launch-1.0 multifilesrc location="data/images/DSC0%04d.JPG" start-index=1013 num-buffers=100 caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
#     gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
#     gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true

# # oprion 3  = fakesink
# gst-launch-1.0 multifilesrc location="data/images/DSC0%04d.JPG" start-index=1013 num-buffers=100 caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
#     gst_detection_small_obj  ! videoconvert  ! fakesink sync=true
 


# #!/bin/bash

export TF_CPP_MIN_LOG_LEVEL=5
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
export GST_DEBUG=python:4

# Default values
DIR="data/images"
IDX=1013
NUM_BUFFERS=100
OPTION=2

# Parse command-line arguments
while getopts "d:i:n:o:" opt; do
  case ${opt} in
    d )
      DIR=$OPTARG
      ;;
    i )
      IDX=$OPTARG
      ;;
    n )
      NUM_BUFFERS=$OPTARG
      ;;
    o )
      OPTION=$OPTARG
      ;;
    \? )
      echo "Invalid option: $OPTARG" 1>&2
      exit 1
      ;;
    : )
      echo "Invalid option: $OPTARG requires an argument" 1>&2
      exit 1
      ;;
  esac
done
shift $((OPTIND -1))

# Run the selected option
case $OPTION in
  1)
    # Option 1 = overlay
    gst-launch-1.0 videotestsrc num-buffers=$NUM_BUFFERS ! video/x-raw,width=1920,height=1080 ! videoconvert ! \
        gst_detection_small_obj ! videoconvert ! gst_detection_overlay ! \
        videoconvert ! fpsdisplaysink sync = true
    ;;

  2)
    # Option 2 = multifilesrc plus overlay
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! \
        gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true
    ;;

  3)
    # Option 2 = tiles plus overlay
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
        gst_detection_overlay ! videoconvert ! fpsdisplaysink sync = true
    ;;
  4)
    # Option 3 = fakesink
    gst-launch-1.0 multifilesrc location="${DIR}/DSC0%04d.JPG" start-index=$IDX num-buffers=$NUM_BUFFERS caps="image/jpeg,framerate=5/1" ! jpegdec ! queue ! videoconvert !  \
        gst_detection_small_obj  ! videoconvert  ! fakesink sync=true
    ;;
  *)
    echo "Invalid option: $OPTION" 1>&2
    exit 1
    ;;
esac