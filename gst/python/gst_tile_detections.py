"""
    export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
    gst-launch-1.0 videotestsrc ! videoconvert ! gst_tile_detections left=10 top=20 bottom=10 right=20 ! videoconvert ! xvimagesink

    Based on:
        https://github.com/GStreamer/gst-python/blob/master/examples/plugins/python/audioplot.py

    Caps negotiation:
        https://gstreamer.freedesktop.org/documentation/plugin-development/advanced/negotiation.html?gi-language=c


"""
# Version of package
__version__ = "0.0.1"

import logging
# import timeit
# import math
# import traceback
# import time
import cv2
import numpy as np
from imutils import resize
import pdb
import gi
# from pprint import pprint

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GLib, GstBase  # noqa:F401,F402

from gstreamer.utils import gst_buffer_with_caps_to_ndarray  # noqa:F401,F402
from gstreamer.gst_objects_info_meta import gst_meta_get, gst_meta_write, gst_meta_remove
from small_object_detector import get_tile, putlabel


FORMATS = [f.strip()
           for f in "RGBx,xRGB,BGRx,xBGR,RGBA,ARGB,BGRA,ABGR,RGB,BGR,RGB16,RGB15,GRAY8,GRAY16_LE,GRAY16_BE".split(',')]

# Input caps
IN_CAPS = Gst.Caps(Gst.Structure('video/x-raw',
                                 format=Gst.ValueList(FORMATS),
                                 width=Gst.IntRange(range(1, GLib.MAXINT)),
                                 height=Gst.IntRange(range(1, GLib.MAXINT))))

# Output caps
OUT_CAPS = Gst.Caps(Gst.Structure('video/x-raw',
                                  format=Gst.ValueList(FORMATS),
                                  width=Gst.IntRange(range(1, GLib.MAXINT)),
                                  height=Gst.IntRange(range(1, GLib.MAXINT))))


def clip(value, min_value, max_value):
    """Clip value to range [min_value, max_value]"""
    return min(max(value, min_value), max_value)


class GstTileDetections(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'gst_tile_detections'

    __gstmetadata__ = ("Tile",
                       "Filter/Effect/Video",
                       "Tile Detections and adds to topside of video",
                       "John Newton <johnnewto at gmail dot com>")

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                            Gst.PadDirection.SRC,
                                            Gst.PadPresence.ALWAYS,
                                            OUT_CAPS),
                        Gst.PadTemplate.new("sink",
                                            Gst.PadDirection.SINK,
                                            Gst.PadPresence.ALWAYS,
                                            IN_CAPS))

    __gproperties__ = {
        "tile_width": (GObject.TYPE_INT64,
                 "Width of tile",
                 "Width of each tile displayed on top of video",
                 0,  # min
                 GLib.MAXINT,  # max
                 40,  # default
                 GObject.ParamFlags.READWRITE
                 ),

        "tile_height": (GObject.TYPE_INT64,
                "Height of tile",
                "Height of each tile displayed on top of video",
                0,
                GLib.MAXINT,
                40,
                GObject.ParamFlags.READWRITE
                ),

        "num_tiles": (GObject.TYPE_INT64,
                  "Number of tiles",
                  "Number of tiles displayed on top of video",
                  0,
                  20,
                  10,
                  GObject.ParamFlags.READWRITE
                  )
    }

    def __init__(self):
        super(GstTileDetections, self).__init__()

        self._tile_width = 60
        self._tile_height = 60
        self._num_tiles = 10


    def do_get_property(self, prop: GObject.GParamSpec):

        if prop.name == 'tile_width':
            return self._tile_width
        elif prop.name == 'tile_height':
            return self._tile_height
        elif prop.name == 'num_tiles':
            return self._num_tiles
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == 'tile_width':
            self._tile_width = value
        elif prop.name == 'tile_height':
            self._tile_height = value
        elif prop.name == 'num_tiles':
            self._num_tiles = value
        else:
            raise AttributeError('unknown property %s' % prop.name)


    def do_transform(self, inbuffer: Gst.Buffer, outbuffer: Gst.Buffer, in_caps=None, out_caps=None) -> Gst.FlowReturn:
        """
        https://lazka.github.io/pgi-docs/GstBase-1.0/classes/BaseTransform.html#GstBase.BaseTransform.do_transform
        """

        # try:
        if True:
            detections = gst_meta_get(inbuffer)
            gst_meta_remove(inbuffer)
            # convert Gst.Buffer to np.ndarray
            # pdb.set_trace()
            # print(in_caps)
            if out_caps is not None :
                # this is used in testing
                structure = out_caps.get_structure(0)  # Gst.Structure
                width, height = structure.get_value("width"), structure.get_value("height")
                # logging.debug(f'out_caps {width = } {height = }')

            in_caps = in_caps if in_caps is not None else self.sinkpad.get_current_caps()
            in_image = gst_buffer_with_caps_to_ndarray(inbuffer, in_caps) #  self.sinkpad.get_current_caps())

            out_caps = out_caps if out_caps is not None else self.srcpad.get_current_caps()
            out_image = gst_buffer_with_caps_to_ndarray(outbuffer, out_caps) # self.srcpad.get_current_caps())

            # print(f'{in_image.shape = } {out_image.shape = }')

            h_in, w_in = in_image.shape[:2]
            h_out = out_image.shape[0]
            h = h_out - h_in
            # copy the image to the lower rows  of the output image
            out_image[h:,:] = in_image

            # make tile list, scale it to he output width, and place at top of the output image
            tiles = []

            for cnt, d in enumerate(detections):   # xywh
                l, t, w, h = d['bounding_box']
                # convert to int from yolo format
                l, t, w, h = int(l*w_in), int(t*h_in), int(w*w_in), int(h*h_in)
                # find the centers of the bounding box
                c, r = int(l + w/2), int(t + h/2)
                # make sure that the tile is within the image
                c, r = clip(c, 0, w_in), clip(r, 0, h_in)
                # calc l, t, w, h from center and tile size
                l, t = c - self._tile_width//2, r - self._tile_height//2
                w, h = self._tile_width, self._tile_height
                # pdb.set_trace()

                tile = get_tile(in_image, (t, l), (h, w), copy=True) # copy so any changes affect the image 

                if tile.shape[2] == 3:
                    print(f'{tile.shape = }')
                    tile = cv2.cvtColor(tile, cv2.COLOR_BGR2BGRA)

                # put label count in left top corner
                clr = (255, 0, 0) if cnt < 5 else (0,255,0) if cnt < 10 else (0, 0, 255)  # in order red, green, blue
                # cv2.putText(tile, str(count), (0, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, clr, 1)
                putlabel(tile, f'{cnt}', (0,7), fontScale=0.4, color=clr, thickness=1)
                tiles.append(tile)

            # pdb.set_trace()
            tile_img = np.hstack(tiles)

            tile_img = resize(tile_img, width=out_image.shape[1])
            h = tile_img.shape[0]
            out_image[:h,:] = tile_img

            # scale yolo xywh detections to output image given that the detections are scaled to the input image
            top_padding = (h_out - h_in ) / h_out
            scale = h_in / h_out
    
            for d in detections:   # xywh
                a = d['bounding_box']
                a[1] = a[1] * scale + top_padding
                a[3] = a[3] * scale


            # pprint(f'{detections = }')
            # pdb.set_trace()
            gst_meta_remove(outbuffer)
            gst_meta_write(outbuffer, detections)

            # out_image[:h,:] = in_image
       
        # except Exception as e:
        #     logging.error(e)

        return Gst.FlowReturn.OK

    def do_transform_caps(self, direction: Gst.PadDirection, caps: Gst.Caps, filter_: Gst.Caps) -> Gst.Caps:
        caps_ = IN_CAPS if direction == Gst.PadDirection.SRC else OUT_CAPS

        if filter_:
            # https://lazka.github.io/pgi-docs/Gst-1.0/classes/Caps.html#Gst.Caps.intersect
            # create new caps that contains all formats that are common to both
            caps_ = caps_.intersect(filter_)

        return caps_

    def do_fixate_caps(self, direction: Gst.PadDirection, caps: Gst.Caps, othercaps: Gst.Caps) -> Gst.Caps:
        """
            caps: initial caps
            othercaps: target caps
        """
        # print(f'{direction = } {caps = } {othercaps = }')
        if direction == Gst.PadDirection.SRC:
            return othercaps.fixate()
        else:
            # Fixate only output caps
            in_width, in_height = [caps.get_structure(0).get_value(v) for v in ['width', 'height']]
            
            # tiles are added to top of video
            scale =  in_width / (self._num_tiles * self._tile_width)
            extra_height = int(self._tile_height * scale)

            width = in_width 
            height = in_height + extra_height
            # print(f'do_fixate_caps {width = } {height = }')

            new_format = othercaps.get_structure(0).copy()

            # https://lazka.github.io/pgi-docs/index.html#Gst-1.0/classes/Structure.html#Gst.Structure.fixate_field_nearest_int
            a = new_format.fixate_field_nearest_int("width", width)
            b = new_format.fixate_field_nearest_int("height", height)
 
            # print(f'{a} {b} {new_format.get_value("width") = } {new_format.get_value("height") = } {new_format.to_string()} ')  
            new_caps = Gst.Caps.new_empty()
            new_caps.append_structure(new_format)
            width, height = new_caps.get_structure(0).get_value("width"), new_caps.get_structure(0).get_value("height")
            # print(f'##### new_caps {width = } {height = }')

            # https://lazka.github.io/pgi-docs/index.html#Gst-1.0/classes/Caps.html#Gst.Caps.fixate
            return new_caps.fixate()

    def do_set_caps(self, incaps: Gst.Caps, outcaps: Gst.Caps) -> bool:

        in_w, in_h = [incaps.get_structure(0).get_value(v) for v in ['width', 'height']]
        out_w, out_h = [outcaps.get_structure(0).get_value(v) for v in ['width', 'height']]

        # if input_size == output_size set plugin to passthrough mode
        # https://gstreamer.freedesktop.org/documentation/additional/design/element-transform.html?gi-language=c#processing
        if in_h == out_h and in_w == out_w:
            self.set_passthrough(True)

        return True


# Register plugin to use it from command line
GObject.type_register(GstTileDetections)
__gstelementfactory__ = (GstTileDetections.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstTileDetections)
