"""
Usage
    export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
    export GST_DEBUG=python:4

    gst-launch-1.0 filesrc location=video.mp4 ! decodebin ! videoconvert ! \
        gst_detection_small_obj config=data/small_object_api_cfg.yml ! videoconvert ! autovideosink
"""

import os
import sys
import logging
import pdb
import traceback
import cv2
# from ultralytics import YOLO
import typing as typ
import yaml
import numpy as np

from gstreamer import Gst, GObject, GstBase, GstVideo
import gstreamer.utils as utils
from gstreamer.gst_objects_info_meta import gst_meta_write, gst_meta_remove

from small_object_detector import CMO_Peak
from small_object_detector import setGImages, getGImages
from small_object_detector import resize

def _get_log_level() -> int:
    return int(os.getenv("GST_PYTHON_LOG_LEVEL", logging.DEBUG / 10)) * 10


log = logging.getLogger('gst_python')
log.setLevel(_get_log_level())


# todo jn
# def create_config(device: str = 'CPU', *,  jn
#                   per_process_gpu_memory_fraction: float = 0.0,
#                   log_device_placement: bool = False) -> tf.ConfigProto:
# def create_config(device: str = 'CPU', *,
#                   per_process_gpu_memory_fraction: float = 0.0,
#                   log_device_placement: bool = False):
#     # """Creates tf.ConfigProto for specifi device"""
#     # config = tf.compat.v1.ConfigProto(log_device_placement=log_device_placement)
#     if is_gpu(device):
#         if per_process_gpu_memory_fraction > 0.0:
#             config.gpu_options.per_process_gpu_memory_fraction = per_process_gpu_memory_fraction
#         else:
#             config.gpu_options.allow_growth = True
#     else:
#         config.device_count['GPU'] = 0

#     return config



# Dummy results for YOLOv8
class Result:
    def __init__(self, conf, xywh, cls):
        self.conf = []
        self.xywh = []
        self.cls = []
        for i in range(5) :
            self.conf.append(conf)
            self.xywh.append(xywh.copy())
            self.cls.append(cls)
            xywh[0] += 110
            xywh[1] += 50


    def numpy(self):
        self.conf = np.array(self.conf)
        self.xywh = np.array(self.xywh)
        self.cls = np.array(self.cls)
        return self



class GstDetectionSmallObjPluginPy(GstBase.BaseTransform):

    # Metadata Explanation:
    # http://lifestyletransfer.com/how-to-create-simple-blurfilter-with-gstreamer-in-python-using-opencv/

    GST_PLUGIN_NAME = 'gst_detection_small_obj'

    __gstmetadata__ = ("Name",
                       "Transform",
                       "Description",
                       "Author")

    _srctemplate = Gst.PadTemplate.new('src', Gst.PadDirection.SRC,
                                       Gst.PadPresence.ALWAYS,
                                       Gst.Caps.from_string("video/x-raw,format=RGB"))

    _sinktemplate = Gst.PadTemplate.new('sink', Gst.PadDirection.SINK,
                                        Gst.PadPresence.ALWAYS,
                                        Gst.Caps.from_string("video/x-raw,format=RGB"))

    __gsttemplates__ = (_srctemplate, _sinktemplate)

    # Explanation: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#GObject.GObject.__gproperties__
    # Example: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#properties
    __gproperties__ = {
        "model": (str,
                  "model",
                  "YOLOv8",
                  None,  # default
                  GObject.ParamFlags.READWRITE),

        "config": (str,
                   "Path to config file",
                   "not sure if needed , Contains path to config *.yml supported by ultralytics YOLOv8 model (e.g. yolov8n.yaml)",
                   None,  # default
                   GObject.ParamFlags.READWRITE
                   ),
    }

    def __init__(self):
        super().__init__()

        self.model = None
        # print("Loading yolov8n model")
        # self.model = YOLO('yolov8m.pt')
        self.config = None
        pypath = sys.executable  # full path of the currently running Python interpreter.
        spath =sys.path
        # pdb.set_trace()
        self.detecter = CMO_Peak(confidence_threshold=0.1,
                        labels_path='data/imagenet_class_index.json',
                        # labels_path='/media/jn/0c013c4e-2b1c-491e-8fd8-459de5a36fd8/home/jn/data/imagenet_class_index.json',
                        expected_peak_max=60,
                        peak_min_distance=5,
                        num_peaks=10,
                        maxpool=12,
                        morph_kernalsize=3,
                        morph_op='BH+filter',
                        track_boxsize=(80, 160),
                        bboxsize=40,
                        draw_bboxes=True,
                        device=None, )


    def do_transform_ip(self, buffer: Gst.Buffer, caps=None, test=False) -> Gst.FlowReturn:
        # if test is True: then the plugin is being tested. Caps needs to be sent as an argument

        # if self.model is None:
        #     Gst.warning(f"No model specified for {self}. Plugin working in passthrough mode")
        #     return Gst.FlowReturn.OK

        if caps is None:
            caps = self.sinkpad.get_current_caps()

        try:
            # Convert Gst.Buffer to np.ndarray
            # pdb.set_trace()
            image = utils.gst_buffer_with_caps_to_ndarray(buffer, caps)
            # print(f'{self} {image.shape = } {buffer.pts = } {buffer.dts = } {buffer.duration = } {buffer.offset = }')
            detections = self.detect(image)

            # write objects to as Gst.Buffer's metadata
            # Explained: http://lifestyletransfer.com/how-to-add-metadata-to-gstreamer-buffer-in-python/
            # if not buffer.is_writable():
            # buffer = buffer.make_writable()
            if test:
                return detections

            gst_meta_write(buffer, detections)


        except Exception as err:
            # pdb.set_trace()
            logging.error("Error %s: %s", self, err)
            traceback.print_exc()
            pass


        return Gst.FlowReturn.OK
    
    def detect(self, image) -> typ.List:
        import time
        start_time = time.time()
        # if self.model is None:
        #     Gst.warning(f"No model specified for {self}. Plugin working in passthrough mode")
        #     return Gst.FlowReturn.OK

        # try:
        setGImages(image)
        getGImages().mask_sky()
        # cv2_img_show('find_sky_2-mask', getGImages().mask, flags=cv2.WINDOW_NORMAL)

        self.detecter.small_objects()
        self.detecter.detect()
        # print(self.detecter.bbwhs)
        # disp_image = self.detecter.display_results(image)

        detections = []
        for i, xywh in enumerate(self.detecter.bbwhs):
            # x = int(1  * (xywh[0] - xywh[2]//2))
            # y = int(1 * (xywh[1] - xywh[3]//2))
            # w = int(1  * xywh[2])
            # h = int(1 * xywh[3])
            # print(f'{i = } {xywh = }')

            detections.append({
                'confidence': 0.9,
                'bounding_box': xywh,
                'class_name': str(i),
            })


        # Calculate and print the execution time
        execution_time = time.time() - start_time
        print(f"The execution time of small-object-detection is {execution_time} seconds")
        return detections
    


    def do_get_property(self, prop: GObject.GParamSpec):
        # pdb.set_trace()
        if prop.name == 'model':
            return self.model
        if prop.name == 'config':
            return self.config
        else:
            raise AttributeError('Unknown property %s' % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        # pdb.set_trace()
        # if prop.name == 'model':
        #     self._do_set_model(value)
        # el
        if prop.name == "config":
            # self._do_set_model(from_config_file(value))
            self.config = value
            Gst.info(f"Model's config updated from {self.config}")
        else:
            raise AttributeError('Unknown property %s' % prop.name)

    # def _do_set_model(self, model):
    #     import gc
    #     # stop previous instance
    #     # pdb.set_trace()
    #     if self.model:
    #         # Currently, the Ultralytics library doesn’t provide a specific method to 'close' or 'destroy' the model
    #         del model
    #         # Collect garbage
    #         gc.collect()

    #     self.model = YOLO(model)

        # # start new instance
        # if self.model:
        #     self.model.startup()

    def __exit__(self, exc_type, exc_val, exc_tb):

        Gst.info(f"Shutdown {self}")

        if self.model:
            self.model.shutdown()

        Gst.info(f"Destroyed {self}")


# Required for registering plugin dynamically
# Explained: http://lifestyletransfer.com/how-to-write-gstreamer-plugin-with-python/
GObject.type_register(GstDetectionSmallObjPluginPy)
__gstelementfactory__ = (GstDetectionSmallObjPluginPy.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstDetectionSmallObjPluginPy)
