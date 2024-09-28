import network
from settings import *
from time import sleep


class Wifi:    
    
    wlan = network.WLAN(network.AP_IF)
    
    def start_ap(self):
        self.wlan.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
        self.wlan.config(essid=SSID, password=PASSWORD)
        self.wlan.active(True)
        while not self.wlan.active():
            pass
        if DEBUG: print(f"AP Up {self.wlan.ifconfig()}")
        
    def connect(self):
        #Connect to WLAN
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
