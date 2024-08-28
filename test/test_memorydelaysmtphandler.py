"""
Unit test for MemoryDelayHandler.
"""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from memorydelaysmtphandler.memorydelaysmtphandler import MemoryDelayHandler
from memorydelaysmtphandler.memorydelaysmtphandler import MemoryDelaySmtpHandler
import logging, logging.handlers
import io, time

__author__  = "void127001"
__version__ = "1.0.0"
__date__    = "27 August 2024"



def log_in_stream(capacity, delay, sleep_duration, line_count, flushOnClose=True):
    """
    Create a stream string, a MemoryDelayHandler(capacity, delay).
    Write into log x line_count and sleep sleep_duration.
    Return the stream string.
    """
    stream = io.StringIO() 
    handler_out = logging.StreamHandler(stream)        

    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(MemoryDelayHandler(capacity, delay, logging.ERROR, handler_out, flushOnClose))

    for i in range(line_count):
        logger.info("Log index = %d", i)
        time.sleep(sleep_duration)

    return stream

def count_line(str):
    """
    Count the number of lines in a string buffer.
    """
    return str.count('\n')

class MyTest(unittest.TestCase):

    def test_nodelay_log_equal_capacity(self):
        """
        No flush delay (equivalent to MemoryHandler).
        Log the capacity.
        Expected result => log size = capacity size
        """
        stream = log_in_stream(capacity=2, delay=None, sleep_duration=0, line_count=2)
        self.assertEqual(count_line(stream.getvalue()), 2)
        logging.shutdown()  
        logging.getLogger().handlers.clear()      

    def test_nodelay_log_less_capacity_no_flushOnClose(self):
        """
        No flush delay (equivalent to MemoryHandler). 
        Check no flushOnClose
        Log less than the capacity.
        Expected result before handler closed => log is empty
        Expected result after handler closed => log is empty
        """
        stream = log_in_stream(capacity=3, delay=None, sleep_duration=0, line_count=2, flushOnClose=False)
        self.assertEqual(count_line(stream.getvalue()), 0)
        logging.getLogger().handlers[0].close()
        self.assertEqual(count_line(stream.getvalue()), 0)
        logging.shutdown()                
        logging.getLogger().handlers.clear()

    def test_nodelay_log_less_capacity_flushOnClose(self):
        """
        No flush delay (equivalent to MemoryHandler). 
        Check flushOnClose
        Log less than the capacity.
        Expected result before handler closed => log is empty
        Expected result after handler closed => log is flushed
        """
        stream = log_in_stream(capacity=3, delay=None, sleep_duration=0, line_count=2, flushOnClose=True)
        self.assertEqual(count_line(stream.getvalue()), 0)
        logging.getLogger().handlers[0].close()
        self.assertEqual(count_line(stream.getvalue()), 2)
        logging.shutdown()        
        logging.getLogger().handlers.clear()


    def test_delay2s_log_equal_capacity_fast(self):
        """
        Flush delay 2s. 
        Log the capacity quickly (before delay).
        Expected result => log size = capacity size
        """
        stream = log_in_stream(capacity=2, delay=2, sleep_duration=0.1, line_count=2)
        self.assertEqual(count_line(stream.getvalue()), 2)
        logging.shutdown()        
        logging.getLogger().handlers.clear()

    def test_delay2s_log_equal_capacity_slow(self):
        """
        Flush delay 2s. 
        Log the capacity slowly (after delay).
        Expected result => log size = capacity size
        """
        stream = log_in_stream(capacity=2, delay=0.5, sleep_duration=1, line_count=2)
        self.assertEqual(count_line(stream.getvalue()), 2)
        logging.shutdown()        
        logging.getLogger().handlers.clear()

    def test_delay2s_log_less_capacity(self):
        """
        Flush delay 2s. 
        Log less than the capacity.
        Expected result before delay => log size = log is empty
        Expected result after delay => log is flushed
        """
        stream = log_in_stream(capacity=3, delay=2, sleep_duration=0.1, line_count=2)
        self.assertEqual(count_line(stream.getvalue()), 0)
        time.sleep(2.5)
        self.assertEqual(count_line(stream.getvalue()), 2)
        logging.shutdown()        
        logging.getLogger().handlers.clear()

    def test_delay2s_log_more_capacity(self):
        """
        Flush delay 2s. 
        Log more than the capacity.
        Expected result before delay => log size = capacity size
        Expected result after delay => log is flushed
        """        
        stream = log_in_stream(capacity=2, delay=2, sleep_duration=0.1, line_count=3)
        self.assertEqual(count_line(stream.getvalue()), 2)
        time.sleep(2.5)
        self.assertEqual(count_line(stream.getvalue()), 3)
        logging.shutdown()        
        logging.getLogger().handlers.clear()

    @unittest.skip("Filling valid SMTP parameters are required for this test")
    def test_delay_smtp(self):
        """
        Flush delay 1s. 
        Log less than the capacity.
        Expected result : an email with 2 logs after the delay 
        """        
        logger = logging.getLogger("")
        logger.setLevel(logging.DEBUG)
        #!!! Fill with valid SMTP parameters !!!
        logger.addHandler(MemoryDelaySmtpHandler(
            mailhost=["your.smtp.com", 25], 
            fromaddr="noreply@yourdomain.com", 
            toaddrs=["youraddress@gmail.com"], 
            subject="Test MemoryDelaySmtpHandler",
            credentials=["yourlogin", "password"], 
            secure=[], 
            timeout=5, 
            capacity=3, 
            delay=1))
        #Create 2 logs
        for i in range(2):
            logger.info("Info index = %d", i)
            time.sleep(0.1)
        time.sleep(3)
        logging.shutdown()
        logging.getLogger().handlers.clear()
        #Check manually if an emails has been received with 2 logs
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()