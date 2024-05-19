"""
Usage
    export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/venv/lib/gstreamer-1.0/:$PWD/gst/
    export GST_DEBUG=python:4

    gst-launch-1.0 filesrc location=video.mp4 ! decodebin ! videoconvert ! \
        gst_tf_detection config=data/tf_object_api_cfg.yml ! videoconvert ! \
        gst_detection_overlay ! videoconvert ! autovideosink
"""

import os
import logging
import random
import sys
import typing as typ
import numpy as np
import cairo

from gstreamer import Gst, GObject, GstBase, GLib
from gstreamer import map_gst_buffer
import gstreamer.utils as utils
from gstreamer.gst_objects_info_meta import gst_meta_get
import pdb

def _get_log_level() -> int:
    return int(os.getenv("GST_PYTHON_LOG_LEVEL", logging.DEBUG / 10)) * 10


log = logging.getLogger('gst_python')
log.setLevel(_get_log_level())


class ColorPicker:
    """Generates random colors"""

    def __init__(self):
        self._color_by_id = {}

    def get(self, idx: typ.Any):
        if idx not in self._color_by_id:
            self._color_by_id[idx] = self.generate_color()
        return self._color_by_id[idx]

    def generate_color(self, low=0, high=1):
        return random.uniform(low, high), random.uniform(low, high), random.uniform(low, high)


class ObjectsOverlayCairo:
    """Draws objects on video frame"""

    def __init__(self, line_thickness_scaler: float = 0.0015,
                 font_size_scaler: float = 0.007,
                 font_family: str = 'Sans',
                 font_slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
                 font_weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
                 text_color: typ.Tuple[int, int, int] = [255, 255, 255],
                 colors: ColorPicker = None,
                 alpha: float = 0.4):

        self.line_thickness_scaler = line_thickness_scaler
        self.font_size_scaler = font_size_scaler
        self.font_family = font_family
        self.font_slant = font_slant
        self.font_weight = font_weight

        self.text_color = [float(x) / max(text_color) for x in text_color]
        self.colors = colors or ColorPicker()
        self.alpha = alpha

    @property
    def log(self) -> logging.Logger:
        return log

    def draw(self, buffer: Gst.Buffer, width: int, height: int, detections: typ.List[dict]) -> bool:
        """Draws objects on video buffer"""

        
        try:
            # print("buffer =", len(buffer), "should be", width*height*4)  # FIXME pixel  needs to be 4 bytes long!
            stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24, width)
            surface = cairo.ImageSurface.create_for_data(buffer,cairo.FORMAT_RGB24, width, height, stride)
            context = cairo.Context(surface)

        except Exception as err:
            logging.error("Failed to create cairo surface for buffer %s. %s", err, self)
            return False

        try:

            context.select_font_face(self.font_family, self.font_slant, self.font_weight)

            diagonal = (width**2 + height**2)**0.5
            context.set_font_size(int(diagonal * self.font_size_scaler))
            context.set_line_width(int(diagonal * self.line_thickness_scaler))

            for i, obj in enumerate(detections):

                # set color by class_name
                b, g, r = (1.0, 0.0, 0.0) if i < 5 else (0.0, 1.0, 0.0) if i < 10 else (0.0, 0.0, 1.0)
                # r, g, b = self.colors.get(obj["class_name"])
                context.set_source_rgba(r, g, b, self.alpha)

                # draw bounding box
                l, t, w, h = obj['bounding_box']
                # convert to int from yolo format
                l, t, w, h = int(l*width), int(t*height), int(w*width), int(h*height)
                context.rectangle(l, t, w, h)
                context.stroke()

                # tableu for additional info
                text = "{}".format(obj["class_name"])
                _, _, text_w, text_h, _, _ = context.text_extents(text)

                t = t-height//400
                tableu_height = text_h
                
                context.set_source_rgba(1,1,1, self.alpha)
                context.rectangle(l, t - tableu_height, w//2, tableu_height)
                context.fill()

                # draw class name
                # r, g, b = self.text_color
                b, g, r = (1.0, 0.0, 0.0) if i < 5 else (0.0, 1.0, 0.0) if i < 10 else (0.0, 0.0, 1.0)
                context.set_source_rgba(r, g, b, 1)
                context.move_to(l, t)
                context.show_text(text)

        except Exception as err:
            logging.error("Failed cairo render %s. %s", err, self)
            return False

        return True

    def get_tile(self, src_surface, l, t, w, h):
        """Returns the image tile at (l, t, w, h)"""
        # Create a new surface of the same size as the rectangle
        new_surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)

        # Create a new context for the new surface
        new_context = cairo.Context(new_surface)

        # Set the source to the original surface
        new_context.set_source_surface(src_surface, -l, -t)

        # Draw a rectangle the same size as the new surface
        new_context.rectangle(0, 0, w, h)

        # Fill the rectangle to copy the pixels
        new_context.fill()
        return new_surface



    def get_tiles(self, buffer: Gst.Buffer, width, height, objects: typ.List[dict]) -> bool:
        """Draws objects on video buffer"""
        try:
            # print("buffer =", len(buffer), "should be", width*height*4)  # FIXME pixel  needs to be 4 bytes long!
            stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24, width)
            surface = cairo.ImageSurface.create_for_data(buffer,cairo.FORMAT_RGB24, width, height, stride)
            context = cairo.Context(surface)

        except Exception as err:
            logging.error("Failed to create cairo surface for buffer %s. %s", err, self)
            return False
        tiles = []
        for i, obj in enumerate(objects):
            l, t, w, h = obj['bounding_box']
            # get the image tile at (l, t, w, h)
            tiles.append(self.get_tile(surface, l, t, w, h))

        # horizontal concat the tiles
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
        context = cairo.Context(surface)
        for i, tile in enumerate(tiles):
            context.set_source_surface(tile, 0, i * h)
            context.paint()
        return surface
    



class GstDetectionOverlay(GstBase.BaseTransform):

    # Metadata Explanation:
    # http://lifestyletransfer.com/how-to-create-simple-blurfilter-with-gstreamer-in-python-using-opencv/

    GST_PLUGIN_NAME = 'gst_detection_overlay'

    __gstmetadata__ = ("Name",
                       "Transform",
                       "Description",
                       "Author")

    _srctemplate = Gst.PadTemplate.new('src', Gst.PadDirection.SRC,
                                       Gst.PadPresence.ALWAYS,
                                       Gst.Caps.from_string("video/x-raw,format={RGBx}"))

    _sinktemplate = Gst.PadTemplate.new('sink', Gst.PadDirection.SINK,
                                        Gst.PadPresence.ALWAYS,
                                        Gst.Caps.from_string("video/x-raw,format={RGBx}"))

    __gsttemplates__ = (_srctemplate, _sinktemplate)

    # Explanation: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#GObject.GObject.__gproperties__
    # Example: https://python-gtk-3-tutorial.readthedocs.io/en/latest/objects.html#properties
    __gproperties__ = {
        "model": (GObject.TYPE_PYOBJECT,
                  "ObjectsOverlayCairo",
                  "Contains model that implements ObjectsOverlayCairo",
                  GObject.ParamFlags.READWRITE),
    }

    def __init__(self):
        super().__init__()

        self.model = ObjectsOverlayCairo()
        self.width = None
        self.height = None
    
    def set_width(self, width):
        self.width = width

    def set_height(self, height):
        self.height = height


    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        import time
        start_time = time.time()
        if self.model is None:
            Gst.warning(f"No model speficied for {self}. Plugin working in passthrough mode")
            return Gst.FlowReturn.OK

        try:
            objects = gst_meta_get(buffer)

            if objects:
                if not self.width or not self.height:
                    self.width, self.height = utils.get_buffer_size_from_gst_caps(self.sinkpad.get_current_caps())

                # Do drawing
                with map_gst_buffer(buffer, Gst.MapFlags.READ | Gst.MapFlags.WRITE) as mapped:
                    self.model.draw(mapped, self.width, self.height, objects)
                    # self.model.put_tiles(objects)

        except Exception as err:
            Gst.error(f"Error {self}: {err}")
            return Gst.FlowReturn.ERROR

        # Calculate and print the execution time
        execution_time = time.time() - start_time
        print(f"The execution time of gst-detection-overlay is {execution_time} seconds")
        return Gst.FlowReturn.OK

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == 'model':
            return self.model
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == 'model':
            self.model = value
        else:
            raise AttributeError('unknown property %s' % prop.name)


# Required for registering plugin dynamically
# Explained: http://lifestyletransfer.com/how-to-write-gstreamer-plugin-with-python/
GObject.type_register(GstDetectionOverlay)
__gstelementfactory__ = (GstDetectionOverlay.GST_PLUGIN_NAME,
                         Gst.Rank.NONE, GstDetectionOverlay)

# unuded stuff

def to_gst_buffer(
        buffer: typ.Union[Gst.Buffer, np.ndarray],
        *,
        pts: typ.Optional[int] = None,
        dts: typ.Optional[int] = None,
        offset: typ.Optional[int] = None,
        duration: typ.Optional[int] = None
) -> Gst.Buffer:
    """Convert buffer to Gst.Buffer. Updates required fields
    Parameters explained:
        https://lazka.github.io/pgi-docs/Gst-1.0/classes/Buffer.html#gst-buffer
    """
    gst_buffer = buffer
    if isinstance(gst_buffer, np.ndarray):
        gst_buffer = Gst.Buffer.new_wrapped(bytes(buffer))

    if not isinstance(gst_buffer, Gst.Buffer):
        raise ValueError(
            "Invalid buffer format {} != {}".format(type(gst_buffer), Gst.Buffer)
        )

    gst_buffer.pts = pts or GLib.MAXUINT64
    gst_buffer.dts = dts or GLib.MAXUINT64
    gst_buffer.offset = offset or GLib.MAXUINT64
    gst_buffer.duration = duration or GLib.MAXUINT64
    return gst_buffer

def gstmap2cairo(self,im1):
    import array
    import cairo
    from PIL import Image
    """Transform a PIL Image into a Cairo ImageSurface.
        https://stackoverflow.com/questions/7610159/convert-pil-image-to-cairo-imagesurface
    """
    im= Image.frombuffer("RGB", (1920, 1080), im1, 'raw', "RGB", 0, 1)
    assert sys.byteorder == 'little', 'We don\'t support big endian'
    if im.mode != 'RGBA':
        im = im.convert('RGBA')

    s = im.tobytes('raw', 'BGRA')
    a = array.array('B', s)
    gst_buffer = Gst.Buffer.new_wrapped(bytes(s))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, im.size[0], im.size[1])
    ctx = cairo.Context(surface)
    non_premult_src_wo_alpha = cairo.ImageSurface.create_for_data(a, cairo.FORMAT_RGB24, im.size[0], im.size[1])
    non_premult_src_alpha = cairo.ImageSurface.create_for_data(a, cairo.FORMAT_ARGB32, im.size[0], im.size[1])
    ctx.set_source_surface(non_premult_src_wo_alpha)
    ctx.mask_surface(non_premult_src_alpha)
    return surface, ctx, gst_buffer

