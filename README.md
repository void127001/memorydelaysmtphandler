# memorydelaysmtphandler

## Overview
**memorydelaysmtphandler** adds new handlers for the Python logging package.

Issue : SMTPHandler sends one email after each event. Multiple emails can be received in a short time.<br> 
Improvement : MemoryDelaySmtpHandler will create a bundle of events in an single email and sent it after a delay.

## Features

**MemoryDelayHandler** class adds an auto-flush delay to logging.handlers.MemoryHandler.<br>
**MemoryDelaySmtpHandler** class adds an auto-flush delay to logging.handlers.SMTPHandler.

#### The handler is flushed when:
- the number of events is equal to the capacity
- the event of a certain severity occurs
- after a first event, the delay is reached

#### New parameters
- Initializes the handler with a buffer of the specified capacity. Here, capacity means the number of events records buffered.
- A delay in seconds to automatically flush the buffer after a first event. When the delay argument is not present or None, no automatic flushed is provided.

## Installation
```
$ python3 -m pip install memorydelaysmtphandler
```



## Using with OpenCanary

logging.handlers.SMTPHandler sends one email after each alert. Multiple emails can be received in a short time.<br> 
MemoryDelaySmtpHandler will create a bundle of alerts in an single email and sent it after a delay.

#### Installation for OpenCanary
Install memorydelaysmtphandler in the OpenCanary environment.

#### Edit /etc/opencanaryd/opencanary.conf
Change "class": "logging.handlers.SMTPHandler"<br>
by     "class": "memorydelaysmtphandler.memorydelaysmtphandler.MemoryDelaySmtpHandler"

add these parameters:
```
	"capacity" : your capacity,
	"delay" : your delay
```    

Example:
```
// [..] # Services configuration
    "logger": {
    "class" : "PyLogger",
    "kwargs" : {
        "handlers": {
            "SMTP": {
                "class": "memorydelaysmtphandler.memorydelaysmtphandler.MemoryDelaySmtpHandler",
                "mailhost": ["smtp.gmail.com", 587],
                "fromaddr": "noreply@yourdomain.com",
                "toaddrs" : ["youraddress@gmail.com"],
                "subject" : "OpenCanary Alert",
                "credentials" : ["youraddress", "abcdefghijklmnop"],
                "secure" : [],
                "capacity" : 128,
                "delay" : 60                
             }
         }
     }
 }
 ```
