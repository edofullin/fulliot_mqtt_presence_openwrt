from subprocess import PIPE, Popen
from threading import Thread, Timer
from python_arptable import get_arp_table
from daemonize import Daemonize

import time
import paho.mqtt.client as mqtt
import json
import logging
import os
import traceback

logging.basicConfig(filename="/var/log/mpd.log",
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

config = {}
monitored_mac = []

mqtt_client = None

def update_hass_state(mac, state):
    
    device_name = next((item for item in config["monitored_devices"] if item["mac"] == mac), None) # find name of device

    logger.info("Reolved device {} to name {}".format(mac, device_name))

    if device_name is None or not mqtt_client.is_connected(): # dev is not monitored
        return
    
    mqtt_client.publish(config["mqtt_state_topic"].replace('$DEV', device_name["name"]), state, 0, True)
    

def send_dev_updates():

    while True:
        logger.info("Updating all devices")

        # report all monitored devices
        lat_arp_table = get_arp_table()

        logger.info(monitored_mac)

        for device in monitored_mac: # report status of devices in monitor list

            logger.info("Updating device {}".format(device))

            dev_arp = next((item for item in lat_arp_table if item["HW address"] == device), None) # check if device in arp table
            
            logger.info("device {} in arptable has flag {}".format(device, "NF" if dev_arp is None else dev_arp["Flags"]))

            if dev_arp is not None:
                try:
                    update_hass_state(device, "connected" if dev_arp["Flags"] == "0x2" else "not_connected") # report home only if dev in arp and flag is 2
                except Exception as exc:
                    logger.error(traceback.print_exc())
                

        time.sleep(30)



def receive_ubus_updates():
    process = Popen(["ubus", "listen", "hostmanager.devicechanged"], stdin=PIPE, stdout=PIPE, bufsize=1)

    while True:
        str = process.stdout.readline().decode('utf-8') # every time ubus throws a new line check if it is a connected device
        logger.info(str)
        js = json.loads(str)["hostmanager.devicechanged"]

        # a newly connected device is reported immediately to trigger automations
        if js["state"] == "connected":
            mac = js["mac-address"]  # str
            state = js["state"]
            
            logger.info("device with mac {} new state: {}".format(mac, state))

            if mac in monitored_mac:            
                update_hass_state(mac, state if state == "connected" else "not_connected")

def mqtt_connected(client, userdata, flags, rc):
    client.publish(config["mqtt_will_topic"], "online", 2, True)


def main():
    global monitored_mac
    global config
    global mqtt_client

    with open("./config.json", "r") as file:
        config = json.load(file)

    monitored_mac = map(lambda elem: elem["mac"], config["monitored_devices"])

    mqtt_client = mqtt.Client(config["mqtt_clientid"], 1883, 60)
    
    mqtt_client.username_pw_set(config["mqtt_username"], config["mqtt_password"])
    mqtt_client.will_set(config["mqtt_will_topic"], "offline", 2, True)
    mqtt_client.on_connect = mqtt_connected

    mqtt_client.connect(config["mqtt_host"])
    # mqtt_client.publish(config["mqtt_will_topic"], "online", 2, True)

    uthread = Thread(target=receive_ubus_updates)
    uthread.daemon = False
    uthread.start()

    sthread = Thread(target=send_dev_updates)
    sthread.daemon = True
    sthread.start()

    mqtt_client.loop_forever()


if __name__ == "__main__":
    deamon = Daemonize(app="mqtt_presence_detection", pid="/tmp/mpd.pid", action=main, verbose=True, chdir=os.path.dirname(os.path.abspath(__file__)))
    deamon.start()

    

