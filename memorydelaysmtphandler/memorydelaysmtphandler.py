"""
memorydelaysmtphandler adds handlers for the Python logging package.
MemoryDelayHandler class and MemorySMTPHandler class
"""

import logging, logging.handlers
import threading, sys, time, io

__author__  = "void127001"
__status__  = "production"
__version__ = "1.0.0"
__date__    = "27 August 2024"
__license__ = "LGPLv2.1"


class MemoryDelayHandler(logging.handlers.MemoryHandler):
    """
    A handler class which buffers logging records in memory, periodically
    flushing them to a target handler. Flushing occurs whenever the buffer
    is full, or when an event of a certain severity or after a delay.
    MemoryDelayHandler class adds an auto-flush delay to logging.handlers.MemoryHandler
    """
    def __init__(self, capacity, delay=None, flushLevel=logging.ERROR, target=None,
                 flushOnClose=True):
        """
        Initialize the handler with the buffer size, the delay for an auto-flush, the level at which
        flushing should occur and an optional target.

        New parameters
            - Initializes the handler with a buffer of the specified capacity. 
            Here, capacity means the number of events records buffered.
            - A delay in seconds to automatically flush the buffer after a first event. 
            When the delay argument is not present or None, no automatic flushed is provided.

        The handler is flushed when:
            - the number of events is equal to the capacity
            - the event of a certain severity occurs
            - after a first event, the delay is reached
        """        
        logging.handlers.MemoryHandler.__init__(self, capacity, flushLevel, target, flushOnClose)

        assert (delay==None) or (not (delay<0)), "delay parameter must be positive."

        #_delay : waiting time before the auto_flush_buffer thread flushes the buffer
        self._delay = delay
        #_event_new_emit : emit() set this event. The auto_flush_buffer thread will flush the buffer after delay wait
        self._event_new_emit = threading.Event()
        #_event_delay_flush : used by the auto_flush_buffer thread to wait the delay duration. If the main thread flush(), this event is set to reset the auto_flush_buffer thread.
        self._event_delay_flush = threading.Event()
        #_barrier : barrier to synchronize the flush between the main and _thread_auto_flush_buffer threads
        self._barrier = threading.Barrier(2)
        #_thread_closing : request to close the _thread_auto_flush_buffer
        self._thread_closing = False
        #_thread_auto_flush_buffer : this thread flushes the buffer after the delay
        self._thread_auto_flush_buffer = threading.Thread(target=self._task_auto_flush_buffer)
        #_append_buffer : during the flush, all the records will be appended to a single string buffer (required for SMTP) 
        self._append_buffer = False

        #_lock_sync : lock to data access between threads. Next variables must be locked
        self._lock_sync = threading.Lock()
        #_sync_backgroud_flush [lock] : request to make a synchronization between threads after a flush
        self._sync_backgroud_flush = False

        #start the _thread_auto_flush_buffer thread
        self._thread_auto_flush_buffer.start()

    def emit(self, record):
        """
        Override def logging.handlers.MemoryHandler.emit
        Send event _event_new_emit to _task_auto_flush_buffer thread.
        If a flush is processed by this main thread, then the _task_auto_flush_buffer is reset. 
        """

        #emit() & flush() are processed with _lock_sync acquired, to synchronize the _task_auto_flush_buffer thread
        self._lock_sync.acquire() 
        self._event_new_emit.set()
        logging.handlers.MemoryHandler.emit(self, record)
        
        #if function flush() is called by the emit(), then reset the _task_auto_flush_buffer thread
        if self._sync_backgroud_flush:
            #request the reset of _task_auto_flush_buffer
            self._event_delay_flush.set()
            self._lock_sync.release()
            self._barrier.wait()
            self._lock_sync.acquire() 
            self._sync_backgroud_flush = False            
            self._event_new_emit.clear()
            self._event_delay_flush.clear()
            self._lock_sync.release()
            self._barrier.wait()
            #_task_auto_flush_buffer has been reset
        else:
            self._lock_sync.release()


    def flush(self):
        """
        Override def logging.handlers.MemoryHandler.flush
        """        
        local_lock_sync = False
        if not self._lock_sync.locked():
            #emit() already locked the _lock_sync.
            #need to lock _lock_sync if not yet locked (call from logging.shutdown())
            local_lock_sync = True
            self._lock_sync.acquire() 
        if (len(self.buffer) >= 1):
            if (self._append_buffer) and (len(self.buffer) > 1):
                MemoryDelayHandler._flush_to_append_buffer_buffer(self)
            else:
                logging.handlers.MemoryHandler.flush(self)
        if local_lock_sync:
            self._lock_sync.release() 
        else:
            #_lock_sync is already locked
            #_sync_backgroud_flush = True, to inform emit() function that the buffer has been flushed by the main thread. Need to reset the _task_auto_flush_buffer thread.
            self._sync_backgroud_flush = True


    def _flush_to_append_buffer_buffer(self):
        """
        Appends the records in single string stream
        """        
        stream_append = io.StringIO() 
        terminator = '\n'
        self.acquire()
        try:
            if self.target:
                #format all records into stream_append
                for record in self.buffer:
                    msg = self.format(record)
                    stream_append.write(msg + terminator)
                #use the first record and replace the msg by the appends string stream
                if (len(self.buffer)>0):
                    record = self.buffer[0]
                    record.msg = stream_append.getvalue()
                    record.args = None
                    record.formatter= None
                    #send the appended record
                    self.target.handle(record)
                self.buffer.clear()
        finally:
            self.release()
        stream_append.close()



    def close(self):
        """
        Override def logging.handlers.MemoryHandler.close
        Request to close the _task_auto_flush_buffer thread.
        """        
        self._lock_sync.acquire()
        self._sync_backgroud_flush = True        
        self._thread_closing = True
        self._event_new_emit.set()
        self._event_delay_flush.set()
        self._lock_sync.release()
        self._thread_auto_flush_buffer.join()
        logging.handlers.MemoryHandler.close(self)

           

    def _task_auto_flush_buffer(self):
        """
        _task_auto_flush_buffer fluses the buffer after a delay
        1. Wait a new emited event
        2. Wait the delay duration. Is a flush() is processed by the main thread then stop to wait and return to reset status
        3. Synchronize with 2 barriers if necessary
        """
        while not self._thread_closing:
            #0. The reset status

            #1. Wait a new emited event
            self._event_new_emit.wait()
            need_wait_barrier = False
            #2. Wait the delay duration. Is a flush() is processed by the main thread then stop to wait and return to reset status
            if (not self._event_delay_flush.wait(self._delay)):
                #after the delay, check is the buffer is not empty, and flush it
                self._lock_sync.acquire()
                if (len(self.buffer) >= 1):
                    if (self._append_buffer) and (len(self.buffer) > 1):
                        MemoryDelayHandler._flush_to_append_buffer_buffer(self)
                    else:
                        logging.handlers.MemoryHandler.flush(self)
                if self._sync_backgroud_flush:
                    need_wait_barrier = True    
                else:
                    self._event_new_emit.clear()
                self._lock_sync.release()
            else:
                #The event _event_delay_flush has been triggered. Need to make the sychronization with the main thread
                need_wait_barrier = True
            if need_wait_barrier and (not self._thread_closing):
                #Do the sychronization with the main thread. Double barrier to reset the event from the main thread
                self._barrier.wait()
                self._barrier.wait()


class MemoryDelaySmtpHandler(MemoryDelayHandler):
    """
    A handler class which sends an SMTP email for a logging events bundle after a delay.
    MemoryDelaySmtpHandler class adds an auto-flush delay to logging.handlers.SMTPHandler.
    MemoryDelaySmtpHandler will create a bundle of events in an single email and sent it after a delay.
    """
    def __init__(self, mailhost, fromaddr, toaddrs, subject,
                 credentials=None, secure=None, timeout=5.0, capacity=32, delay=10.0, flushLevel=logging.CRITICAL):
        #Create the SMTPHandler output
        SMTPHandlerOutput = logging.handlers.SMTPHandler(mailhost, fromaddr, toaddrs, subject,
                 credentials, secure, timeout)
        #Initialize MemoryDelayHandler
        MemoryDelayHandler.__init__(self, capacity=capacity, delay=delay, flushLevel=flushLevel, 
                target=SMTPHandlerOutput, flushOnClose=True)
        self._append_buffer = True
        
