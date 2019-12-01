# OPENWRT MQTT Presence Detection
A Python service that sends a mqtt message when specified devices connect/disconnect

This is a python script that listens for ubus events related to a device connection and every 30 seconds checks arp table to get the full list of connected devices.

Because of this approch when a device connects the mqtt packet is sent immediately and any automation connected to it is triggered immediately.
On the other hand when a device disconnects it can take some time for the script to see it disconnected (it is marked disconnected when it is not present on the arp table or when its flag is set to 0x0) and because of that this script handles quick disconnections and reconnections.

# Compatibility

The part that sends connection messages immediately will work only on OpenWRT since it requires specific messages on ubus, I might make the script work without that part as well to make it compatible with any linux distro.

This script is tested on OPENWRT 15.05 Chaos Chalmer and on Python 2.7 (should also work on python 3.x but I cannot confirm)

# Installation

To run this script you have to install the requirements via pip:
```bash
pip install -r requirements.txt 
```

And then you should create a config.txt file in the same directory as the script with this structure:
```json
{
    "monitored_devices": [
        {"name": "device1", "mac": "aa:bb:cc:dd:ee:ff"}, 
        {"name": "device2", "mac": "aa:bb:cc:dd:ee:ff"}, 
        {"name": "device3", "mac": "aa:bb:cc:dd:ee:ff"}, 
        {"name": "device4", "mac": "aa:bb:cc:dd:ee:ff"}
    ],
    "mqtt_host": "...",
    "mqtt_username": "...",
    "mqtt_password": "...",
    "mqtt_will_topic": "home/dev_tracking/available",
    "mqtt_state_topic": "home/dev_tracking/$DEV/state",
    "mqtt_clientid": "devtrack"
}
```
You can customize those parameters in any way you need.
MQTT username and password can be set to ```none``` to disable mqtt authentication

The will message payload is 'online' / 'offline'
$DEV represents the name of the device as defined in the monitored_devices section

You can run the script directly with ```python PATH_TO_MAIN.py```

Otherwise you can set up your system to start the program at boot by setting it up as a service.
If you use OpenWRT you can copy the mqtt_arp_presence to your /etc/init.d directory, change the startup command to the directory where you put your main.py and then run
```bash
/etc/init.d/mqtt_arp_presence enable
/etc/init.d/mqtt_arp_presence start
```

This way it will start at every boot. (more info [here](https://openwrt.org/docs/techref/initscripts))

# Usage

I created this program because I couldn't find a way to use presence detection in home assistant.
LUCI RPC did not work on my particular router and was too slow to report when a device connected, bluetooth wouldn't work because I usually keep it off on my phone and gps draws too much battery.

This script solved all problems, as soon as I enter in the WiFi range the phone connects and all my automations start!

To set it up with home assistant you must have a MQTT broker and configure device_tracker as in [this](https://www.home-assistant.io/integrations/device_tracker.mqtt) article _(remember to set payload_home to connected and payload_not_home to not_connected)_.

# Pull Request

Any new feature, bug fix or anything is appreciated.
Make a pull request if you can!



