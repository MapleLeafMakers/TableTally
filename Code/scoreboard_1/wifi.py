import network
from settings import *
from time import sleep


class Wifi:    
    wlan = network.WLAN(network.STA_IF)

    def connect(self):
        #Connect to WLAN
        self.wlan.ifconfig(('192.168.4.10', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        self.wlan.active(True)
        self.wlan.connect(SSID, PASSWORD)
        i=0
        while self.wlan.isconnected() == False:
            i+=1
            if DEBUG: print(f'Waiting for connection...{i}')
            sleep(1)
        ip = self.wlan.ifconfig()[0]
        if DEBUG: print(f'Connected on {ip}')
        return ip
    
    def disconnect(self):
        self.wlan.active(False)

