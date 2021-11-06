#!/usr/bin/env python

"""Configurable python service to run on Raspberry Pi
   and use pin GPIO3 (SCL) to trigger system shutdown
"""

__author__ = "Michael Heise"
__copyright__ = "Copyright (C) 2021 by Michael Heise"
__license__ = "Apache License Version 2.0"
__version__ = "1.0.3"
__date__ = "11/06/2021"

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
import logging
import signal
import subprocess
import sys
import time
import weakref

# 3rd party imports
import gpiozero as GPIO
from systemd.journal import JournalHandler

# local imports
# - none -


class RaspiGPIOShutdown:
    """Encapsulate GPIO3-triggered shutdown logic for Raspberry Pi."""

    CONFIGFILE = "/etc/raspi-gpio3-shutdown.conf"
    VALUESEVENT = ["press", "release", "hold", "holdrelease"]

    def __init__(self):
        """Initialize RaspiGPIOShutdown instance."""
        self._finalizer = weakref.finalize(self, self.finalize)

        self.isValidGPIO = False
        self.config = None
        self.trigger_shutdown = False

    def remove(self):
        """Call finalizer when object is removed."""
        self._finalizer()

    @property
    def removed(self):
        return not self._finalizer.alive

    def finalize(self):
        """Set validation field to false."""
        self.isValidGPIO = False

    def initLogging(self, log):
        """Initialize logging to journal."""
        log_fmt = logging.Formatter("%(levelname)s %(message)s")
        logHandler = JournalHandler()
        logHandler.setFormatter(log_fmt)
        log.addHandler(logHandler)
        log.setLevel(logging.INFO)
        # log.setLevel(logging.DEBUG)
        self._log = log
        self._log.info("Initialized logging.")

        pinf = type(GPIO.Device._default_pin_factory()).__name__
        self._log.info(f"GPIO Zero default pin factory: {pinf}")
        return

    def readConfigFile(self):
        """Read the config file."""
        try:
            self._log.info(f"Reading configuration file... '{self.CONFIGFILE}'")
            self.config = configparser.ConfigParser()
            self.config.read(self.CONFIGFILE)
            return True
        except Exception:
            self._log.error(f"Accessing config file '{self.CONFIGFILE}' failed!")
            return False

    def initGPIO(self):
        """Evaluate the data read from config file to
        set the GPIO input
        """
        self._log.info("Init GPIO configuration.")
        configGPIO = self.config["GPIO"]

        self._log.info("Button configuration = '{0}'".format(configGPIO["Button"]))

        buttonConfig = configGPIO["Button"].lower().split(",")

        if not buttonConfig[0] in self.VALUESEVENT:
            self._log.error(
                "Invalid shutdown configuration! "
                + "Only 'PRESSED', 'RELEASED', 'HOLD' or 'HOLDRELEASE' allowed!"
            )
            return False

        try:
            if len(buttonConfig) == 2:
                hold_time = float(buttonConfig[1])
                if hold_time <= 0.0:
                    raise
            else:
                hold_time = 2.0
        except Exception:
            self._log.error(
                "Invalid hold time! (only float >0 specifying time in seconds allowed)"
            )
            return False

        try:
            # configure GPIO3 as input (with internal hard-wired I²C pullup)
            self.btn = GPIO.Button(3)
            self.btn.hold_time = hold_time

            method_name = "config_" + buttonConfig[0]
            self._log.info(f"Configure GPIO3 with action '{method_name}'")

            configbtn = getattr(self, method_name)
            configbtn()

            self.isValidGPIO = True
            return True
        except Exception:
            self._log.error("Error while setting up GPIO3 input for shutdown button!")
            return False

    def config_press(self):
        """Configure button to trigger event handler when pressed"""
        self._wasbtnheld = True
        self.btn.when_pressed = self.handle_btn_event

    def config_release(self):
        """Configure button to trigger event handler when released"""
        self._wasbtnheld = True
        self.btn.when_released = self.handle_btn_event

    def config_hold(self):
        """Configure button to trigger event handler when held pressed for at least hold_time"""
        self._wasbtnheld = True
        self.btn.when_held = self.handle_btn_event

    def config_holdrelease(self):
        """Configure button to trigger event handler when was held pressed and released again"""
        self._wasbtnheld = False
        self.btn.when_held = self.held_pressed_btn
        self.btn.when_released = self.handle_btn_event

    def handle_btn_event(self):
        """Handle the configured button event.
        If _wasbtnheld was set before, set shutdown flag."""
        self._log.info("Button action at GPIO3 was handled.")
        if self._wasbtnheld:
            # set variable to quit service while-loop
            self.trigger_shutdown = True

    def held_pressed_btn(self):
        """Handle button held pressed event and set the respective flag to true."""
        self._log.info("Button at GPIO3 was held pressed.")
        self._wasbtnheld = True


def sigterm_handler(_signo, _stack_frame):
    """Clean exit on SIGTERM signal (when systemd stops the process)"""
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
        time.sleep(1)

    log.info("Initiate system shutdown after GPIO3 button event handled.")

    import shlex

    cmd = shlex.split("sudo shutdown -h now")
    subprocess.call(cmd, shell=False)

except Exception as e:
    if log:
        log.exception("Unhandled exception: {0}".format(e.args[0]))
    sys.exit(-1)
finally:
    if shutdown and shutdown.isValidGPIO:
        if log:
            log.info("Ending raspi-gpio3-shutdown service.")
