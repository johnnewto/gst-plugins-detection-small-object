import queue

import threading
import time
from functools import partial

import pdb
from gi.repository import Gst, GLib, GObject, GstApp, GstRtp, GstVideo  # noqa:F401,F402
from gstreamer import GstPipeline, CallbackHandler, LogLevels
from gstreamer.utils import *
import attr

@attr.s(slots=True, frozen=True)
class GstBuffer:
    data = attr.ib()  # type: np.ndarray
    pts = attr.ib(default=GLib.MAXUINT64)  # type: int
    dts = attr.ib(default=GLib.MAXUINT64)  # type: int
    offset = attr.ib(default=GLib.MAXUINT64)  # type: int
    duration = attr.ib(default=GLib.MAXUINT64)  # type: int



class LeakyQueue(queue.Queue):
    """Queue that contains only the last actual items and drops the oldest one."""

    def __init__(
        self,
        maxsize: int = 100,
        on_drop: typ.Optional[typ.Callable[["LeakyQueue", "object"], None]] = None,
    ):
        super().__init__(maxsize=maxsize)
        self._dropped = 0
        self._on_drop = on_drop or (lambda queue, item: None)

    def put(self, item, block=True, timeout=None):
        if self.full():
            dropped_item = self.get_nowait()
            self._dropped += 1
            self._on_drop(self, dropped_item)
        super().put(item, block=block, timeout=timeout)

    @property
    def dropped(self):
        return self._dropped

class GstBufferSrc(GstPipeline):
    """Gstreamer Video Source Base Class

    Usage Example:
        >>> width, height, num_buffers = 1920, 1080, 100
        >>> caps_filter = 'capsfilter caps=video/x-raw,format=RGB,width={},height={}'.format(width, height)
        >>> command = 'videotestsrc num-buffers={} ! {} ! appsink emit-signals=True sync=false'.format(
        ...     num_buffers, caps_filter)
        >>> with GstBufferSrc(command) as pipeline:
        ...     buffers = []
        ...     while len(buffers) < num_buffers:
        ...         buffer = pipeline.pop()
        ...         if buffer:
        ...             buffers.append(buffer)
        ...     print('Got: {} buffers'.format(len(buffers)))
        >>>
    """

    def __init__(self, command: str,  # Gst_launch string
                 leaky: bool = False,  # If True -> use LeakyQueue
                 max_buffers_size: int = 100,  # Max queue size,
                 callback_handler : typ.Union[CallbackHandler, None] = None,
                 loglevel: typ.Union[LogLevels, int] = LogLevels.INFO):  # debug flags
        """
        :param command: gst-launch-1.0 command (last element: appsink)
        """
        super(GstBufferSrc, self).__init__(command, loglevel=loglevel)

        self._sink = None  # GstApp.AppSink
        # self.callback_handler = callback_handler
        self.callback_handler= callback_handler
        self._counter = 0  # counts number of received buffers

        queue_cls = partial(LeakyQueue, on_drop=self._on_drop) if leaky else queue.Queue
        self._queue = queue_cls(maxsize=max_buffers_size)  # Queue of GstBuffer


    def startup(self):
        super().startup()
        if self.callback_handler:
            self._thread = threading.Thread(target=self._app_thread)
            self._thread.start()

        return self


    def _app_thread(self):
        # self._end_jpeg_capture_event.clear()
        self._start_tracking_thread_is_done = False
        while not self.is_done and not self._end_stream_event.is_set():
            buffer = self.get_nowait()
            if not buffer:
                pass
                # self.log.warning("No buffer")
            else:
                self.callback_handler.callback(self.callback_handler.id, self.callback_handler.name, buffer)
                # self.log.info(f"Got buffer: {buffer.data.shape = } {buffer.pts = } {buffer.dts = }")
                # run tracker, send frame
            time.sleep(0.01)

        self.log.info('Sending EOS event')
        self.pipeline.send_event(Gst.Event.new_eos())

        # self.log.info(f'Waiting for pipeline to shutdown {self._end_stream_event.is_set() = }')
        while self.is_active:
            self.log.info('Waiting for pipeline to shutdown')
            time.sleep(.1)

        # self.log.info(f'Waiting for pipeline to shutdown {self.is_active = }')
        # self.log.info(f'Waiting for pipeline to shutdown {self.is_done = }')


    @property
    def total_buffers_count(self) -> int:
        """Total read buffers count """
        return self._counter

    @staticmethod
    def _clean_queue(q: queue.Queue):
        while not q.empty():
            try:
                q.get_nowait()
            except queue.Empty:
                break

    def _on_drop(self, queue: LeakyQueue, buffer: GstBuffer) -> None:
        self.log.warning(
            "Buffer #%d for %s is dropped (totally dropped %d buffers)",
            int(buffer.pts / buffer.duration),
            self,
            queue.dropped,
        )

    def _on_pipeline_init(self):
        """Sets additional properties for plugins in Pipeline"""

        appsinks = self.get_by_cls(GstApp.AppSink)
        self._sink = appsinks[0] if len(appsinks) == 1 else None
        if not self._sink:
            # TODO: force pipeline to have appsink
            raise AttributeError("%s not found", GstApp.AppSink)

            # TODO jn ENSURE video_frmt: GstVideo.VideoFormat = GstVideo.VideoFormat.RGB,  # gst specific (RGB, BGR, RGBA)
        # Listen to 'new-sample' event
        # https://lazka.github.io/pgi-docs/GstApp-1.0/classes/AppSink.html#GstApp.AppSink.signals.new_sample
        if self._sink:
            self._sink.connect("new-sample", self._on_buffer, None)

    def _extract_buffer(self, sample: Gst.Sample) -> typ.Optional[GstBuffer]:
        """Converts Gst.Sample to GstBuffer

        Gst.Sample:
            https://lazka.github.io/pgi-docs/Gst-1.0/classes/Sample.html
        """
        buffer = sample.get_buffer()
        # self._last_buffer = buffer  # testcode

        caps = sample.get_caps()

        cnt = buffer.n_memory()
        if cnt <= 0:
            self.log.warning("%s No data in Gst.Buffer", self)
            return None

        memory = buffer.get_memory(0)
        if not memory:
            self.log.warning("%s No Gst.Memory in Gst.Buffer", self)
            return None

        array = gst_buffer_with_caps_to_ndarray(buffer, caps, do_copy=True)
        if len(array.shape) < 3:
            self.log.error(f'{self} Invalid array shape: {array.shape}, perhaps add "capsfilter caps=video/x-raw,format=RGB" to pipeline')

        # print(array.shape)
        return GstBuffer(
            data=array,
            pts=buffer.pts,
            dts=buffer.dts,
            duration=buffer.duration,
            offset=buffer.offset,
        )

    def _on_buffer(self, sink: GstApp.AppSink, data: typ.Any) -> Gst.FlowReturn:
        """Callback on 'new-sample' signal"""
        # Emit 'pull-sample' signal
        # https://lazka.github.io/pgi-docs/GstApp-1.0/classes/AppSink.html#GstApp.AppSink.signals.pull_sample

        sample = sink.emit("pull-sample")

        if isinstance(sample, Gst.Sample):
            caps = sample.get_caps()
            structure = caps.get_structure(0)  # Gst.Structure

            width, height = structure.get_value("width"), structure.get_value("height")
            if height == 1080:
                print(f' ignoring 1080p data from multifilesrc: {width = } {height = }')
                return Gst.FlowReturn.OK
            
            nparray = self._extract_buffer(sample).data
            buffer = sample.get_buffer()
  

            # print(f'_on_buffer: {nparray.shape = } {buffer.pts = } {buffer.dts = } {buffer.duration = } {buffer.offset = }')
            # pdb.set_trace()

            self._queue.put( (nparray, buffer.copy_deep(), caps.copy(), sample) ) # Make a copy of the buffer
            # self._queue.put(self._extract_buffer(sample))
            self._counter += 1
            return Gst.FlowReturn.OK

        self.log.error(
            "Error : Not expected buffer type: %s != %s. %s",
            type(sample),
            Gst.Sample,
            self,
        )
        return Gst.FlowReturn.ERROR

    def pop(self, timeout: float = 0.1) -> typ.Optional[GstBuffer]:
        """ Pops GstBuffer , waits for timeout seconds"""
        if not self._sink:
            raise RuntimeError("Sink {} is not initialized".format(Gst.AppSink))

        nparray, buffer, caps, sample = None, None, None, None
        #
        # while (self.is_active or not self._queue.empty()) and not buffer:   this was not doing timeout properly
        try:
            (nparray, buffer, caps, sample ) = self._queue.get(timeout=timeout)
        except queue.Empty:
            pass

        return (nparray, buffer, caps, sample)

    def get_nowait(self) -> typ.Optional[GstBuffer]:
        """ Pops GstBuffer without waiting if empty """
        if not self._sink:
            raise RuntimeError("Sink {} is not initialized".format(Gst.AppSink))
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None


    @property
    def queue_size(self) -> int:
        """Returns queue size of GstBuffer"""
        return self._queue.qsize()

    def shutdown(self, timeout: int = 1, eos: bool = False):
        super().shutdown(timeout=timeout, eos=eos)

        self._clean_queue(self._queue)

