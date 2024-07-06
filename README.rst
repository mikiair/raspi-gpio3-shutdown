raspi-gpio3-shutdown
======================
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and use pin GPIO3 to trigger system shutdown.

**raspi-gpio3-shutdown** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only.
The service expects a NO (normally open) button connected to GPIO3 (SCL) and any GND (ground) pin on the Raspberry pin header.
This will on one hand shutdown the system when the button triggers a configured event, 
and on the other hand allows automatically restarting the system with another press of the button.

Required packages
-----------------
* pigpiod (or another supported pin factory library)
* GPIO Zero
* python3-systemd

Installation / Maintenance
--------------------------
Download raspi-gpio3-shutdown via **Code** button or from `Releases <https://github.com/mikiair/raspi-gpio3-shutdown/releases>`_ page (you most likely did already).
Unzip the received file:

   ``unzip raspi-gpio3-shutdown-main.zip -d ~/raspi-gpio-shutdown``

Configure the service by editing the file ``raspi-gpio3-shutdown.conf`` (see Configuration_).
Then simply run the script ``install`` in the **script** sub-folder. It will download and install the required packages, 
copy the files to their destinations, will register the service, and finally start it.

For uninstall, use the second provided script ``uninstall``.

If you need to change the configuration after installation, you might use the script ``reconfigure`` after editing the source configuration file.
This will stop the service, copy the changed configuration file to **/etc** folder (overwrites previous version!), and then start the service again.

Configuration
-------------
The configuration is defined in the file ``raspi-gpio3-shutdown.conf``. Before installation, you will find the source file in the folder where you unzipped the package files. 
After installation, the active version is in **/etc** folder.

The configuration file requires a section ``[GPIO]`` with one mandatory key ``Button``. The ``Button`` key must be created based on this pattern::

  Button = press|release|hold|holdrelease[,holdtime_s]

``press|release|hold|holdrelease``
  Determines the event for triggering the system shutdown.
  
``holdtime_s``
  (*optional*) Defines the time in seconds to trigger an hold button event; default is 2 seconds.

e.g.

``Button = holdrelease,1.5``

configures pin GPIO3 to trigger the shutdown after the button has been held for at least 1.5s and was finally released.
