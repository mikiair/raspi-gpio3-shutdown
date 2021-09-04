raspi-gpio3-shutdown
======================
This is a configurable Python service to run on `Raspberry Pi <https://www.raspberrypi.org>`_ and use pin GPIO3 to trigger system shutdown.

**raspi-gpio3-shutdown** runs a Python script as a service on Raspberry Pi. It uses the `GPIO Zero <https://github.com/gpiozero/gpiozero>`_ package which allows 
selecting among various underlying pin factories. Tested with `pigpio <http://abyz.me.uk/rpi/pigpio/index.html>`_ library only.
The service expects a NO (normally open) button connected to GPIO3 (SCL) and any GND (ground) pin on the Raspi pin header.
This will on one hand trigger system shutdown when the button releases a configured event, 
and on the other hand allows automatically restarting the system with another press of the button.

Installation / Maintenance
--------------------------
After download, configure the serive by editing the file ``raspi-gpio3-shutdown.conf`` (see Configuration_). 
Then simply run the script ``install`` in the **script** sub-folder. It will download all required packages, 
copy the files to their destinations, will register the service, and finally start it.

For uninstall, use the second provided script ``uninstall``.

If you like to change the configuration while your system is running, you might use the script ``restart``. 
This will copy the changed configuration file to **/etc** folder (overwrites previous version!), and then restart the service. 

Configuration
-------------

The configuration is defined in the file ``raspi-gpio3-shutdown.conf``. Before installation, you will find it in the
folder where you unzipped the package files. After installation, the active version is in **/etc** folder.

The configuration file requires a section ``[GPIO]`` with one mandatory key ``Button``. The ``Button`` key must be created based on this pattern::

  Button = press|release|hold|holdrelease[,holdtime_s]

``press|release|hold|holdrelease``
  Determines the event for triggering the system shutdown.
  
``holdtime_s``
  (*optional*) Defines the time in seconds to trigger an hold button event; default is 2 seconds.

e.g.

``Button = holdrelease,1.5``

configures pin GPIO3 to trigger the shutdown after the button has been held for at least 1.5s and was finally released.
