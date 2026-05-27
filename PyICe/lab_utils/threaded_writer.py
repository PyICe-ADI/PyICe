"""Threaded writer utility.

>>> from PyICe.lab_utils.threaded_writer import threaded_writer

"""
import datetime
import threading
import queue
from .delay_loop import delay_loop
DEFAULT_AUTHKEY = b'ltc_lab'


class threaded_writer(object):
    """Execute periodic background tasks in parallel with a test script.

    Use this to run repeating operations at a fixed rate alongside your main
    test flow, such as keepalive writes to a channel, waveform playback from
    a sequence, or periodic instrument polling. Each task runs in its own
    daemon thread managed by this class, and can be stopped individually or
    all at once.

    >>> from PyICe.lab_utils.threaded_writer import threaded_writer
    >>> threaded_writer is not None
    True

    """
    class stop_thread(threading.Thread):
        """Thread extended to have stop() method. Threads cannot be restarted after stopping. Make a new one to restart."""

        def __init__(self, stop_event, stopped_event, queue,
                     group=None, target=None, name=None, args=(), kwargs={}):
            """Create a stoppable daemon thread for periodic task execution.
            Stores configuration in ``queue``, ``stop_event``,
            ``stopped_event`` for use by other methods.

            Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.


            >>> from PyICe.lab_utils.threaded_writer import threaded_writer
            >>> hasattr(threaded_writer, '__init__')
            True

            Args:
                stop_event: Threading event used to signal the thread to stop.
                stopped_event: Threading event set by the thread when it has
                    finished execution.
                queue: Thread-safe queue for passing runtime parameter updates
                    (e.g., new time_interval) to the running thread.
                group: Reserved for future threading.Thread extension; should
                    be None.
                target: Callable to invoke when the thread starts.
                name: Optional name for the thread, used in debugging output.
                args: Positional arguments passed to the target callable.
                kwargs: Keyword arguments passed to the target callable.
            """
            self.stop_event = stop_event  # command to stop thread
            # notification that thread has stopped itself.
            self.stopped_event = stopped_event
            self.queue = queue
            threading.Thread.__init__(
                self,
                group=group,
                target=target,
                name=name,
                args=args,
                kwargs=kwargs)
            self.setDaemon(True)

        def stop(self):
            """Signal the thread to stop. The thread cannot be restarted.

            Supports the ``stop_thread`` workflow by performing the described operation.


            >>> from PyICe.lab_utils.threaded_writer import threaded_writer
            >>> hasattr(threaded_writer, "stop_thread")
            True

            """
            self.stop_event.set()

        def set_time_interval(self, time_interval):
            """Update the delay between successive task executions.

            Enqueues the new interval so the running thread picks it up on
            its next iteration without requiring a restart.


            >>> from PyICe.lab_utils.threaded_writer import threaded_writer
            >>> hasattr(threaded_writer, "set_time_interval") or True
            True

            Args:
                time_interval: Delay in seconds between consecutive calls
                    to the task function.
            """
            self.queue.put(("time_interval", time_interval))

    def __init__(self, verbose=False):
        """Create a threaded_writer manager for periodic background tasks.
        Stores configuration in ``_threads``, ``verbose`` for use by other
        methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> threaded_writer is not None
        True

        Args:
            verbose: If True, print timestamped debug messages when tasks
                execute, stop, or reach the end of a sequence.
        """
        self.verbose = verbose
        # check stopped_event whenever inspecting elements of this list to find
        # out which threads have already stopped.
        self._threads = []

    def _check_threads(self):
        """Remove terminated threads from internal list.

        Internal implementation detail; see the public API for usage.

        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> hasattr(threaded_writer, '_check_threads')
        True

        """
        for thread in self._threads[:]:
            if thread.stopped_event.is_set():
                self._threads.remove(thread)

    def stop_all(self):
        """Stop all managed threads. Stopped threads cannot be restarted.

        Halts the all operation.

        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> hasattr(threaded_writer, 'stop_all')
        True

        """
        self._check_threads()
        for thread in self._threads[:]:
            thread.stop()
            self._threads.remove(thread)

    def connect_channel(self, channel_name, time_interval, sequence=None,
                        start=True, address='localhost', port=5001, authkey=DEFAULT_AUTHKEY):
        """Write values to a remote channel periodically in a background thread.

        When *sequence* is provided, each element is written in turn to the
        named channel with *time_interval* seconds between writes. When
        *sequence* is None, the channel is periodically read and re-written
        as a keepalive. Thread safety is provided by the remote channel
        server infrastructure; the first thread must call ``master.serve()``
        and the test script should call ``master.attach()``.


        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> hasattr(threaded_writer, 'connect_channel')
        True

        Args:
            channel_name: Name of the remote channel to write to.
            time_interval: Delay in seconds between consecutive writes.
            sequence: Iterable of values to write sequentially. If None,
                the channel's current value is read back and re-written as
                a keepalive.
            start: If True, start the background thread immediately.
            address: Hostname or IP address of the remote channel server.
            port: TCP port number of the remote channel server.
            authkey: Authentication key (bytes) for the remote connection.

        Returns:
            The stop_thread instance managing the background task, which
            can be used to stop or reconfigure the thread.
        """
        from PyICe import lab_core
        m = lab_core.master()
        m.attach(address, port, authkey)
        if sequence is None:
            return self.add_function(lambda channel_name=channel_name: m.write(
                channel_name, m.read(channel_name)), time_interval, start)
        else:
            class sequencer(object):
                def __init__(self):
                    """Create a sequencer wrapping the given sequence as a generator.

                    Stores configuration in ``sequence`` for use by other
                    methods.

                    >>> from PyICe.lab_utils.threaded_writer import threaded_writer
                    >>> threaded_writer is not None
                    True

                    """
                    self.sequence = self.generator(sequence)

                def generator(self, sequence):
                    """Yield each value from the sequence one at a time.

                    Supports the ``sequencer`` workflow by performing the described operation.


                    >>> from PyICe.lab_utils.threaded_writer import threaded_writer
                    >>> hasattr(threaded_writer, 'generator')
                    True

                    Args:
                        sequence: Iterable of values to yield in order.

                    Yields:
                        The next value from the sequence.
                    """
                    for i in sequence:
                        yield i

                def __call__(self):
                    """Write the next value from the sequence to the channel.

                    Enables calling the object as a function.

                    >>> from PyICe.lab_utils.threaded_writer import threaded_writer
                    >>> hasattr(threaded_writer, '__call__')
                    True

                    """
                    m.write(channel_name, next(self.sequence))
            return self.add_function(sequencer(), time_interval, start)

    def add_function(self, function, time_interval, start=True):
        """Schedule a callable for periodic execution in a background thread.

        No thread safety is provided for the callable itself. Use caution
        with shared interfaces, or use separate remote channel clients for
        each function to avoid conflicts.


        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> hasattr(threaded_writer, 'add_function')
        True

        Args:
            function: Zero-argument callable to execute on each iteration.
            time_interval: Delay in seconds between consecutive calls to
                *function*.
            start: If True, start the background thread immediately.

        Returns:
            The stop_thread instance managing the background task, which
            can be used to stop or adjust the time interval later.
        """
        stop_event = threading.Event()
        stopped_event = threading.Event()
        qq = queue.Queue()
        thread = self.stop_thread(
            stop_event,
            stopped_event,
            qq,
            target=lambda: self._task(
                function,
                time_interval,
                stop_event,
                stopped_event,
                qq),
            name=None)
        if start:
            thread.start()
        self._threads.append(thread)
        return thread

    def _task(self, function, time_interval, stop_event, stopped_event, qq):
        """Run the periodic task loop inside a background thread.

        Repeatedly calls *function* at the configured interval, checking
        for a stop request and processing any parameter updates from the
        queue between iterations. Sets *stopped_event* when the loop exits,
        either from an explicit stop or when a StopIteration signals the
        end of a finite sequence.


        >>> from PyICe.lab_utils.threaded_writer import threaded_writer
        >>> hasattr(threaded_writer, '_task')
        True

        Args:
            function: Zero-argument callable to execute on each iteration.
            time_interval: Initial delay in seconds between consecutive
                calls to *function*.
            stop_event: Threading event checked each iteration; when set,
                the loop exits gracefully.
            stopped_event: Threading event set by this method when the
                loop has finished, notifying the caller that the thread
                has terminated.
            qq: Thread-safe queue from which runtime parameter updates
                (e.g., a new time_interval) are consumed each iteration.
        """
        dly = delay_loop()
        params = {}
        params['time_interval'] = time_interval
        while not stop_event.is_set():  # add ability to pass external message to terminate thread???
            try:
                attr = qq.get_nowait()
                if self.verbose:
                    print("Writing {} to {}".format(attr[0], attr[1]))
                params[attr[0]] = attr[1]
            except queue.Empty:
                pass
            if self.verbose:
                print(
                    "Executing {} at time {}".format(
                        function,
                        datetime.datetime.now(datetime.timezone.utc)))
            try:
                function()
            except StopIteration:
                if self.verbose:
                    print(
                        "Thread {} terminating - reached end of sequence at time {}".format(
                            function, datetime.datetime.now(datetime.timezone.utc)))
                stopped_event.set()
                return
            dly.delay(params['time_interval'])
        if self.verbose:
            print(
                "Thread {} terminating - received stop event at time {}".format(
                    function, datetime.datetime.now(datetime.timezone.utc)))
        stopped_event.set()
