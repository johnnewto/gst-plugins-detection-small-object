# gst-plugins-detection-small-object
- based on the good works of https://github.com/jackersson/gst-plugins-tf
- Allows to run small object detector based on https://github.com/johnnewto/SmallObjDetector and inject metadata bounding box labels into Gstreamer Pipeline in Python


[![This might not show in github](docs/mainview.png)](docs/output.mp4) 

see `docs/output.mp4` or 

## Installation 1

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade wheel pip setuptools
pip install --upgrade --requirement requirements.txt
```
### Or Installation 2

Download gst_plugins-detection-small-object from github and create a virtual environment

``` sh
mkdir repos-e .
cd repos
git clone https://github.com/johnnewto/gst-plugins-detection-small-object
cd gst-plugins-detection-small-object
python -m venv 'venv'
source ./venv/bin/activate
pip install --upgrade pip
pip install -e .
```

#### Note: If developing you install small-object-detector local package as editable ()
``` sh

cd gst_plugins-detection-small-object
pip install -e git+file:///home/$USER/PycharmProjects/SmallObjDetector#egg=small_object_detector

```
 With vscode add this to settings.json so that pylance can find the editable package

 ` "python.analysis.extraPaths": ["/home/$USER/PycharmProjects/SmallObjDetector"],`

## Usage

### Run example of use see 
```bash
./scripts/sod-run.sh

```

### To enable plugins implemented in **gst/python**
```bash
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
```

### Plugins
#### gst_detection_small_obj -> gst_tile_detections -> gst_detection_overlay

``` sh 

gst-launch-1.0 multifilesrc location="data/images/DSC0%04d.JPG" start-index=1013 num-buffers=100 caps="image/jpeg,framerate=3/1" ! \
    jpegdec ! queue ! videoconvert !  \
    gst_detection_small_obj  ! videoconvert  ! "video/x-raw,format=RGBA" ! gst_tile_detections !  videoconvert  ! "video/x-raw,format=RGBx" !  \
    gst_detection_overlay ! videoconvert ! \
    fpsdisplaysink sync = true

# to record, replace fpsdisplaysink with this     queue ! x264enc ! mp4mux ! filesink location=image.mp4

```

##### Parameters

 - **config**: Todo



### Additional
To reset the gst registry delete your gstreamer registry (it regenerates itself)
```bash
./scripts/rm_gst_registry.sh 
```

#### Enable/Disable Gst logs
```bash
export GST_DEBUG=python:{0,1,2,3,4,5 ...}
```

#### Enable/Disable Python logs
```bash
export GST_PYTHON_LOG_LEVEL={0,1,2,3,4,5 ...}
```
       

