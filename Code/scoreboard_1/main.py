import time
import sys
import uerrno
import usocket as socket
import neopixel
from wifi import Wifi
import machine
from scoreboard import Scoreboard
from settings import *

STATE_WAITING = 1
STATE_GAME_POINT = 2
STATE_MATCH_POINT = 3
STATE_NO_NETWORK = 4
STATE_WAITING_START = 5

PACKET_LEN = 5

ticks_ms = None
ticks_diff = None

try:
    ticks_diff = time.ticks_diff
    ticks_ms = time.ticks_ms
except AttributeError:
    ticks_diff = lambda x, y: x - y
    ticks_ms = lambda: round(time.time() * 1000)

    
    
class FakeNP(list):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._screen_pos = [
        # Score digit 1
        (13, 1), (14, 1), (15, 1), (16, 1), (17, 1), (18, 1), (19, 1), (20, 1), (21, 1), (22, 1),
        (23, 2), (23, 3), (23, 4), (23, 5), (23, 6), (23, 7), (23, 8), (23, 9), (23, 10), (23, 11),
        (22, 12), (21, 12), (20, 12), (19, 12), (18, 12), (17, 12), (16, 12), (15, 12), (14, 12), (13, 12),
        (11, 12), (10, 12), (9, 12), (8, 12), (7, 12), (6, 12), (5, 12), (4, 12), (3, 12), (2, 12),
        (1, 11), (1, 10), (1, 9), (1, 8), (1, 7), (1, 6), (1, 5), (1, 4), (1, 3), (1, 2),
        (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1), (11, 1),
        (12, 2), (12, 3), (12, 4), (12, 5), (12, 6), (12, 7), (12, 8), (12, 9), (12, 10), (12, 11),

        # Score digit 2
        (13, 14), (14, 14), (15, 14), (16, 14), (17, 14), (18, 14), (19, 14), (20, 14), (21, 14), (22, 14),
        (23, 15), (23, 16), (23, 17), (23, 18), (23, 19), (23, 20), (23, 21), (23, 22), (23, 23), (23, 24),
        (22, 25), (21, 25), (20, 25), (19, 25), (18, 25), (17, 25), (16, 25), (15, 25), (14, 25), (13, 25),
        (11, 25), (10, 25), (9, 25), (8, 25), (7, 25), (6, 25), (5, 25), (4, 25), (3, 25), (2, 25),
        (1, 24), (1, 23), (1, 22), (1, 21), (1, 20), (1, 19), (1, 18), (1, 17), (1, 16), (1, 15),
        (2, 14), (3, 14), (4, 14), (5, 14), (6, 14), (7, 14), (8, 14), (9, 14), (10, 14), (11, 14),
        (12, 15), (12, 16), (12, 17), (12, 18), (12, 19), (12, 20), (12, 21), (12, 22), (12, 23), (12, 24),

        # Match digit
        (13, 27), (14, 27), (15, 27), (16, 27), (17, 27), (18, 27),
        (19, 28), (19, 29), (19, 30), (19, 31), (19, 32), (19, 33),
        (18, 34), (17, 34), (16, 34), (15, 34), (14, 34), (13, 34),
        (11, 34), (10, 34), (9, 34), (8, 34), (7, 34), (6, 34),
        (5, 33), (5, 32), (5, 31), (5, 30), (5, 29), (5, 28),
        (6, 27), (7, 27), (8, 27), (9, 27), (10, 27), (11, 27),
        (12, 28), (12, 29), (12, 30), (12, 31), (12, 32), (12, 33),

        # Serve Dots
        (23, 35), (23, 36), (23, 38), (23, 39)

        ]

    def write(self):
        for (i, (r,g,b)) in enumerate(self):
            l,c = self._screen_pos[i]
            print(f"\x1b[{l};{c*2}H\x1b[38;2;{r};{g};{b}m██", end="")
            print("\x1b[0m")
            print("\x1b[23;0H")
        

def main(display_id):
    np = neopixel.NeoPixel(machine.Pin(4), 186)
    scoreboard = Scoreboard(np)
    scoreboard.handle_update(SCOREBOARD_NUMBER, 88, 8, 8, 100)    
    wifi = Wifi()
    wifi.disconnect()
    my_ip = wifi.connect()
    scoreboard.handle_update(SCOREBOARD_NUMBER, 0, 0, SCOREBOARD_NUMBER + 1, 5)
    print("\x1b[2J")
    # np = FakeNP([(0, 0, 0)] * 186) #neopixel.NeoPixel(machine.Pin(4), 186)

    # while True:
    #     time.sleep(0.01)
    #     scoreboard.tick(ticks_ms())
    
    buffer = b''
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
    except OSError as e:
        raise e
    
    client_socket.setblocking(0)
    
    client_socket.send(bytes([display_id]))

    while True:     
        scoreboard.tick(ticks_ms())
        try:
            inc = client_socket.recv(PACKET_LEN-len(buffer))
            if not inc:
                if DEBUG: print("Conn closed")
                # Connection closed
                break
            buffer += inc
            if DEBUG: print(f"got packet {buffer}")
            if len(buffer) == PACKET_LEN:
                if DEBUG: print("handling update")
                scoreboard.handle_update(buffer[0], buffer[1], buffer[2], buffer[3], buffer[4])
                buffer = b''
        except OSError as e:
            if e.args[0] == uerrno.EAGAIN:
                pass
            else:
                raise e

        
    client_socket.close()
        
        
if __name__ == "__main__":
    main(SCOREBOARD_NUMBER)
