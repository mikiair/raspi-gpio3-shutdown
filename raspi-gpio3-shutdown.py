#!/usr/bin/env python

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__date__ = "08/21/2021"

"""Configurable python service to run on Raspberry Pi
   and use GPIO3 (SCL) for system shutdown
"""

#    Copyright 2021 Michael Heise (mikiair)
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# standard imports
import configparser
import sys
import subprocess
import weakref
import signal
import logging
from systemd.journal import JournalHandler

# 3rd party imports
import gpiozero as GPIO

# local imports
# - none -


class RaspiGPIOShutdown:
    def __init__(self):
        self._finalizer = weakref.finalize(self, self.finalize)
        
        self.isValidGPIO = False
        self.CONFIGFILE = "/etc/raspi-gpio3-shutdown.conf"
        self.valuesEvent = ["press", "release", "hold", "holdrelease"]
        self.config = None
        self.trigger_shutdown = False

    def remove(self):
        self._finalizer()

    @property
    def removed(self):
        return not self._finalizer.alive
    
    def finalize(self):
        self.isValidGPIO = False

    def initLogging(self, log):
        """initialize logging to journal"""
        log_fmt = logging.Formatter("%(levelname)s %(message)s")
        logHandler = JournalHandler()
        logHandler.setFormatter(log_fmt)
        log.addHandler(logHandler)
        log.setLevel(logging.INFO)
        self._log = log
        self._log.info("Initialized logging.")

        pinf = type(gpiozero.Device._default_pin_factory()).__name__
        self._log.info(f"GPIO Zero default pin factory: {pinf}")
        return

    def readConfigFile(self):
        """read the config file"""
        try:
            self._log.info(f"Reading configuration file... '{self.CONFIGFILE}")
            self.config = configparser.ConfigParser()
            self.config.read(self.CONFIGFILE)
            return True
        except Exception:
            self._log.error(f"Accessing config file '{self.CONFIGFILE}' failed!")
            return False

    def initGPIO(self):
        """evaluate the data read from config file to
        set the GPIO input
        """
        self._log.info("Init GPIO configuration.")
        configGPIO = self.config["GPIO"]

        self._log.info("Button configuration = '{0}'".format(configGPIO["Button"]))

        buttonConfig = configGPIO["Button"].lower().split(",")

        if not buttonConfig[0] in self.valuesEvent:
            self._log.error(
                "Invalid shutdown configuration! Only 'PRESSED', 'RELEASED', 'HOLD' or 'HOLDRELEASE' allowed!"
            )
            return False

        try:
            if len(buttonConfig) == 2:
                hold_time = int(buttonConfig[1])
                if hold_time <= 0:
                    raise
            else:
                hold_time = 1500
        except:
            self._log.error("Invalid hold time! (only integer >0 allowed)")
            return false
        
        try:
            # configure GPIO3 as input (with internal hard-wired I²C pullup)
            self.btn = GPIO.Button(3)
            self.btn.hold_time = hold_time
            
            method_name = "config_" + buttonConfig[0]
            self._log.info(f"Configure GPIO3 with '{method_name}'")
            
            configbtn = getattr(self, method_name, lambda: pass)
            configbtn()

            isValidGPIO = True
            return True
        except:
            self._log.error("Error while setting up GPIO3 input for shutdown button!")
            return False

    def config_press(self):
        """Configure button to trigger event handler when pressed
        """
        self._wasbtnheld = True
        self.btn.when_pressed = self.handle_btn_event
    
    def config_release(self):
        """Configure button to trigger event handler when released
        """
        self._wasbtnheld = True
        self.btn.when_released = self.handle_btn_event
    
    def config_hold(self):
        """Configure button to trigger event handler when held pressed for at least hold_time
        """
        self._wasbtnheld = True
        self.btn.when_held = self.handle_btn_event
    
    def config_holdrelease(self):
        """Configure button to trigger event handler when was held pressed and released again
        """
        self._wasbtnheld = False
        self.btn.when_held = self.held_pressed_btn
        self.btn.when_released = self.handle_btn_event

    def handle_btn_event(self):
        self._log.info("Button action at GPIO3 was handled.")
        if self._wasbtnheld:
            # set variable to quit service while-loop
            self.trigger_shutdown = True
        
    def held_pressed_btn(self):
        self._log.info("Button at GPIO3 was held pressed.")
        self._wasbtnheld = True
        
        
def sigterm_handler(_signo, _stack_frame):
    """clean exit on SIGTERM signal (when systemd stops the process)"""
    sys.exit(0)


# install handler
signal.signal(signal.SIGTERM, sigterm_handler)

log = None
shutdown = None

try:
    log = logging.getLogger(__name__)

    shutdown = RaspiGPIOShutdown()
    shutdown.initLogging(log)

    if not shutdown.readConfigFile():
        sys.exit(-2)
        
    if not shutdown.config["GPIO"]:
        log.error("Invalid configuration file! (no [GPIO] section)")
        sys.exit(-3)

    if not shutdown.initGPIO():
        log.error("Init GPIO failed!")
        sys.exit(-3)

    log.info("Enter raspi-gpio3-shutdown service loop...")

    while not shutdown.trigger_shutdown:
        pass

    log.info("Initiate system shutdown after GPIO3 button event handled.")
    subprocess.call(['shutdown', '-h', 'now'], shell=False)

except Exception as e:
    if log:
        log.exception("Unhandled exception: {0}".format(e.args[0]))
    sys.exit(-1)
finally:
    if shutdown and shutdown.isValidGPIO:
        if log:
            log.info("Ending raspi-gpio3-shutdown service.")
