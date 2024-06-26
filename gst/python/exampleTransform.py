#!/usr/bin/python3
# exampleTransform.py
# 2019 Daniel Klamt <graphics@pengutronix.de>
# https://github.com/GStreamer/gst-python/blob/master/examples/plugins/python/exampleTransform.py
# Inverts a grayscale image in place, requires numpy.
# modified using
# gst-launch-1.0 videotestsrc ! ExampleTransform ! videoconvert ! xvimagesink

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gst, GObject, GstBase, GstVideo

# Gst.Buffer.map(Gst.MapFlags.WRITE) is broken, this is a workaround. See
# http://lifestyletransfer.com/how-to-make-gstreamer-buffer-writable-in-python/
from gstreamer import map_gst_buffer

import numpy as np

Gst.init(None)
FIXED_CAPS = Gst.Caps.from_string('video/x-raw,format=GRAY8,width=[1,2147483647],height=[1,2147483647]')

class ExampleTransform(GstBase.BaseTransform):
    __gstmetadata__ = ('ExampleTransform Python','Transform',
                      'example gst-python element that can modify the buffer gst-launch-1.0 videotestsrc ! ExampleTransform ! videoconvert ! xvimagesink', 'dkl')

    __gsttemplates__ = (Gst.PadTemplate.new("src",
                                           Gst.PadDirection.SRC,
                                           Gst.PadPresence.ALWAYS,
                                           FIXED_CAPS),
                       Gst.PadTemplate.new("sink",
                                           Gst.PadDirection.SINK,
                                           Gst.PadPresence.ALWAYS,
                                           FIXED_CAPS))

    def do_set_caps(self, incaps, outcaps):
        struct = incaps.get_structure(0)
        self.width = struct.get_int("width").value
        self.height = struct.get_int("height").value
        return True

    def do_transform_ip(self, buf):
        try:
            with map_gst_buffer(buf, Gst.MapFlags.READ | Gst.MapFlags.WRITE) as info:
                # Create a NumPy ndarray from the memoryview and modify it in place:
                A = np.ndarray(shape = (self.height, self.width), dtype = np.uint8, buffer = info)
                A[:] = np.invert(A)
                return Gst.FlowReturn.OK

        # except Gst.MapError as e:
        except Exception as e:
            Gst.error("Mapping error: %s" % e)
            print("Mapping error: %s" % e)
            # return Gst.FlowReturn.ERROR

GObject.type_register(ExampleTransform)
__gstelementfactory__ = ("ExampleTransform", Gst.Rank.NONE, ExampleTransform)
