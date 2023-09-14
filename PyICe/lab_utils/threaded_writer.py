import datetime, threading, queue
DEFAULT_AUTHKEY = b'ltc_lab'

class threaded_writer(object):
    '''helper to perform some task in parallel with test script at fixed rate'''
    class stop_thread(threading.Thread):
        '''Thread extended to have stop() method. Threads cannot be restarted after stopping. Make a new one to restart.'''
        def __init__(self, stop_event, stopped_event, queue, group=None, target=None, name=None, args=(), kwargs={}):
            self.stop_event = stop_event #command to stop thread
            self.stopped_event = stopped_event #notification that thread has stopped itself.
            self.queue = queue
            threading.Thread.__init__(self, group=group, target=target, name=name, args=args, kwargs=kwargs)
            self.setDaemon(True)
        def stop(self):
            '''stop thread. thread cannot be restarted.'''
            self.stop_event.set()
        def set_time_interval(self, time_interval):
            self.queue.put(("time_interval", time_interval))
    def __init__(self, verbose=False):
        self.verbose = verbose
        self._threads = [] #check stopped_event whenever inspecting elements of this list to find out which threads have already stopped.
    def _check_threads(self):
        '''remove terminated threads from internal list'''
        for thread in self._threads[:]:
            if thread.stopped_event.is_set():
                self._threads.remove(thread)
    def stop_all(self):
        '''stop all threads. threads cannot be restarted.'''
        self._check_threads()
        for thread in self._threads[:]:
            thread.stop()
            self._threads.remove(thread)
    def connect_channel(self, channel_name, time_interval, sequence=None, start=True, address='localhost', port=5001, authkey=DEFAULT_AUTHKEY):
        '''
        Write each element of sequence in turn to channel_name, waiting time_interval between writes.
        If sequence is None, Periodically read and re-write channel as keepalive.
        Thread safety provided by remote channel server infrastructure.
        First thread must call master.serve() and test script should call master.attach().
        '''
        from PyICe import lab_core
        m = lab_core.master()
        m.attach(address, port, authkey)
        if sequence is None:
            return self.add_function(lambda channel_name=channel_name: m.write(channel_name, m.read(channel_name)), time_interval, start)
        else:
            class sequencer(object):
                def __init__(self):
                    self.sequence = self.generator(sequence)
                def generator(self, sequence):
                    for i in sequence:
                        yield i
                def __call__(self):
                    m.write(channel_name, next(self.sequence))
            return self.add_function(sequencer(), time_interval, start)
    def add_function(self, function, time_interval, start=True):
        '''
        Periodically execute function.
        No thread safety. Use caution with shared interfaces or use separate remote channel clients with each function. See example above.
        '''
        stop_event = threading.Event()
        stopped_event = threading.Event()
        qq = queue.Queue()
        thread = self.stop_thread(stop_event, stopped_event, qq, target=lambda: self._task(function, time_interval, stop_event, stopped_event, qq), name=None)
        if start:
            thread.start()
        self._threads.append(thread)
        return thread
    def _task(self, function, time_interval, stop_event, stopped_event, qq):
        '''thread handling loop. processes input Event to request thread termination and sends event back when thread terminates.'''
        dly = delay_loop()
        params = {}
        params['time_interval'] = time_interval
        while not stop_event.is_set(): #add ability to pass external message to terminate thread???
            try:
                attr = qq.get_nowait()
                if self.verbose:
                    print("Writing {} to {}".format(attr[0],attr[1]))
                params[attr[0]] = attr[1]
            except queue.Empty:
                pass
            if self.verbose:
                print("Executing {} at time {}".format(function, datetime.datetime.utcnow()))
            try:
                function()
            except StopIteration as e:
                if self.verbose:
                    print("Thread {} terminating - reached end of sequence at time {}".format(function, datetime.datetime.utcnow()))
                stopped_event.set()
                return
            dly.delay(params['time_interval'])
        if self.verbose:
            print("Thread {} terminating - received stop event at time {}".format(function, datetime.datetime.utcnow()))
        stopped_event.set()