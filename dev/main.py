import cv2
import sys
from gi.repository import Gst, GLib
from gstreamer.utils import *

from dev.gst_buffer_src import GstBufferSrc
from small_object_detector.g_images import getGImages
from small_object_detector import resize, cv2_img_show
if __name__ == '__main__':
    from pprint import pprint
    pypath = sys.executable  # full path of the currently running Python interpreter.
    spath =sys.path
    pprint(sys.path)
    import gst.python.gst_detection_small_obj as test_detection
    import gst.python.gst_detection_overlay as test_overlay
    from gst.python.gst_tile_detections import GstTileDetections, FORMATS

    from pathlib import Path

    # detecter = CMO_Peak(confidence_threshold=0.1,
    #                     labels_path='data/imagenet_class_index.json',
    #                     # labels_path='/media/jn/0c013c4e-2b1c-491e-8fd8-459de5a36fd8/home/jn/data/imagenet_class_index.json',
    #                     expected_peak_max=60,
    #                     peak_min_distance=5,
    #                     num_peaks=10,
    #                     maxpool=12,
    #                     morph_kernalsize=3,
    #                     morph_op='BH+filter',
    #                     track_boxsize=(80, 160),
    #                     bboxsize=40,
    #                     draw_bboxes=True,
    #                     device=None, )

    # from gst.python.gst_detection_small_obj import GstSmallObjDetectionPluginPy

    test_detect_plugin = test_detection.GstDetectionSmallObjPluginPy()
    test_overlay_plugin = test_overlay.ObjectsOverlayCairo()


    home = str(Path.home())
    num_buffers = 20
    caps_filter = 'capsfilter caps=video/x-raw,format=RGB,width={},height={}'.format(6000, 4000)
    command = 'videotestsrc num-buffers={} ! {} ! videoconvert ! appsink emit-signals=True sync=false'.format(  num_buffers, caps_filter)

   
    # path = home + '/data/maui-data/Karioitahi_09Feb2022/132MSDCF-28mm-f4' 
  
    DIR, IDX = '/home/john/data/maui-data/Karioitahi_09Feb2022/132MSDCF-28mm-f4/DSC0%04d.JPG', 1013
    # DIR, IDX = '/home/john/data/maui-data/karioitahi_13Aug2022/SonyA7C/104MSDCF/DSC0%04d.JPG', 7274

    command = f'multifilesrc location="{DIR}" index={IDX} caps="image/jpeg,framerate=3/10" ! jpegdec ! queue ! videoconvert ! \
        videoscale ! video/x-raw,format=RGBx ! appsink emit-signals=True sync=false'


    tile_detections = GstTileDetections()
    # tile_detections.set_property('left', 500)
    # tile_detections.set_property('top', 500)

    # left = tile_detections.get_property('left')
    # right = tile_detections.get_property('right')
    # top = tile_detections.get_property('top')
    # bottom = tile_detections.get_property('bottom')




    with GstBufferSrc(command) as pipeline:

        for i in range(num_buffers):
            (nparray, buffer, caps, sample) = pipeline.pop()
            if buffer:

                # structure = caps.get_structure(0)  # Gst.Structure
                # width, height = structure.get_value("width"), structure.get_value("height")
                # # GstVideo.VideoFormat
                # video_format = gst_video_format_from_string(structure.get_value('format'))
                # channels = get_num_channels(video_format)
                # # channels = _get_num_channels(video_format) 

                detections = test_detect_plugin.do_transform_ip(buffer, caps, test=True)
                # print(detections)

                # create a new output buffer and caps for the cropped image
                # outwidth = nparray.shape[1] - left - right
                # outheight = nparray.shape[0] - top - bottom
                # outarray = np.zeros((outheight, outwidth, 4), dtype='uint8')
                # outbuffer = Gst.Buffer.new_wrapped(bytes(outarray)) 

                outcaps = Gst.Caps(Gst.Structure('video/x-raw',
                                  format=Gst.ValueList(FORMATS),
                                  width=Gst.IntRange(range(1, GLib.MAXINT)),
                                  height=Gst.IntRange(range(1, GLib.MAXINT))))

                # outcaps = Gst.Caps.new_empty()
                # structure = Gst.Structure.new_from_string(f"video/x-raw,format=RGBx, width={outwidth}, height={outheight}")
                # outcaps.append_structure(structure)


                outcaps = tile_detections.do_fixate_caps(None, caps, outcaps)
                # in_width, in_height = [outcaps.get_structure(0).get_value(v) for v in ['width', 'height']]
                out_width, out_height = [outcaps.get_structure(0).get_value(v) for v in ['width', 'height']]
                outarray = np.zeros((out_height, out_width, 4), dtype='uint8')
                # set top 100 rows is yellow
                outarray[:100, :] = [0, 255, 255, 255]
                outbuffer = Gst.Buffer.new_wrapped(bytes(outarray)) 
                tile_detections.do_transform(buffer, outbuffer, in_caps=caps, out_caps=outcaps)

                # scale yolo detections xywh to the output image
                top_padding = (out_height - nparray.shape[0] ) / out_height
                scale = nparray.shape[0] / out_height
       
                for d in detections:   # xywh
                    a = d['bounding_box']
                    a[1] = a[1] * scale + top_padding
                    a[3] = a[3] * scale
   

                # simulate  ! videoconvert ! which would converts to RGBx needed for overlay
                image = gst_buffer_with_caps_to_ndarray(outbuffer, outcaps)
                width, height = image.shape[1], image.shape[0]
                # if channels == 3: # convert to 4 channels
                image = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)

                # setGImages(image)
                # getGImages().mask_sky()
                cv2_img_show('find_sky_2-mask', getGImages().mask, flags=cv2.WINDOW_NORMAL)

                # detecter.small_objects()
                # detecter.detect()
                # disp_image = detecter.display_results(image)

                # cv2_img_show('disp_image', cv2.cvtColor(disp_image, cv2.COLOR_RGB2BGR))
                # k = cv2.waitKey(1)

                gst_buffer = Gst.Buffer.new_wrapped(bytes(image))
                with map_gst_buffer(gst_buffer, Gst.MapFlags.READ | Gst.MapFlags.WRITE) as mapped:

                    test_overlay_plugin.draw(mapped, width, height, detections)
                    # test_overlay_plugin.put_tiles(mapped, width, height, detections)

                    result = np.ndarray(shape=(width, height, 4), buffer=mapped, dtype='uint8')
                    result = result.reshape(height, width, 4).squeeze()
                    # print(f'result.shape={result.shape}')
                    # fullres_tile = get_tile(getGImages().full_rgb, (r - bs, c - bs), (bs * 2, bs * 2), copy=True) # copy so any changes to fullres_cmo_tile_lst do not affect the image
 

                    result = resize(result, width=1920)
                    cv2_img_show('frame', cv2.cvtColor(result, cv2.COLOR_RGB2BGR), mode='BGR')
                    k = cv2.waitKey(1)
                    if k == 27 or k == ord('q'):
                        print('ESC or q pressed. Exiting ...')  # ESC or 'q' to exit
                        break



