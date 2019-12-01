from subprocess import PIPE, Popen
from threading import Thread, Timer
from python_arptable import get_arp_table

import time
import paho.mqtt.client as mqtt
import json

config = None
monitored_mac = []

mqtt_client = None

def update_hass_state(mac, state):
    
    device_name = next((item for item in config["monitored_devices"] if item["mac"] == mac), None) # find name of device

    if device_name is None or not mqtt_client.is_connected(): # dev is not monitored
        return
    
    mqtt_client.publish(config["mqtt_state_topic"].replace('$DEV', device_name["name"]), state, 0, True)
    

def send_dev_updates():

    while True:
        # report all monitored devices
        lat_arp_table = get_arp_table()

        for device in monitored_mac: # report status of devices in monitor list

            dev_arp = next((item for item in lat_arp_table if item["HW address"] == device), None) # check if device in arp table
          
            update_hass_state(device, "connected" if dev_arp is not None and dev_arp["Flags"] == "0x2" else "not_connected") # report home only if dev in arp and flag is 2
            

        time.sleep(30)



def receive_ubus_updates():
    process = Popen(["ubus", "listen", "hostmanager.devicechanged"], stdin=PIPE, stdout=PIPE, bufsize=1)

    while True:
        str = process.stdout.readline().decode('utf-8') # every time ubus throws a new line check if it is a connected device
        print(str)
        js = json.loads(str)["hostmanager.devicechanged"]

        # a newly connected device is reported immediately to trigger automations
        if js["state"] == "connected": 
            mac = js["mac-address"]  # str
            state = js["state"]

            if mac in monitored_mac:            
                update_hass_state(mac, state if state == "connected" else "not_connected")

def mqtt_connected(client, userdata, flags, rc):
    client.publish(config["mqtt_will_topic"], "online", 0, True)

if __name__ == "__main__":
    with open("./config.json", "r") as file:
        config = json.load(file)
    
    monitored_mac = map(lambda elem: elem["mac"], config["monitored_devices"])

    mqtt_client = mqtt.Client(config["mqtt_clientid"], 1883, 60)
    
    mqtt_client.username_pw_set(config["mqtt_username"], config["mqtt_password"])
    mqtt_client.will_set(config["mqtt_will_topic"], "offline", 0, True)
    mqtt_client.on_connect = mqtt_connected

    mqtt_client.connect(config["mqtt_host"])

    uthread = Thread(target=receive_ubus_updates)
    uthread.daemon = False
    uthread.start()

    sthread = Thread(target=send_dev_updates)
    sthread.daemon = True
    sthread.start()

    mqtt_client.loop_forever()

