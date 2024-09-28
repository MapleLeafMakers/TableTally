import random
import time
import usocket as socket
import uselect as select
import uerrno
from picozero import Button
from game import Game, GameState
from wifi import Wifi
from settings import *

poller = select.poll()
clients = {}


ticks_ms = None
ticks_diff = None

g = Game()

try:
    ticks_diff = time.ticks_diff
    ticks_ms = time.ticks_ms
except AttributeError:
    ticks_diff = lambda x, y: x - y
    ticks_ms = lambda: round(time.time() * 1000)


class DisplayClient:
    STATE_WAITING = 1
    STATE_GAME_POINT = 2
    STATE_MATCH_POINT = 3
    STATE_NO_NETWORK = 4
    STATE_WAITING_START = 5
    
    def __init__(self, socket, display_id=None):
        self._sendbuf = b''
        self.socket = socket
        self.display_id = display_id

    def update(self, score=0, match=0, serve=0, state=0):
        data = bytes([self.display_id, score, match, serve, state])
        try:
            sent = self.socket.send(data)
            if sent < 5:
                if DEBUG: print("send incomplete")
                self._sendbuf = data[sent:]
            else:
                if DEBUG: print(f"sent {data}")
        except OSError as e:
            if e.args[0] == uerrno.EAGAIN:
                if DEBUG: print("send blocked")
                self._sendbuf = data
            else:
                raise e
        
    def handle_read(self):
        try:
            data = self.socket.recv(1)
            if data:
                display_id = data[0]
                self.display_id = display_id
                if DEBUG: print(f"Display {display_id} connected.")
            else:
                del clients[self.socket]
                raise IOError(f"Client {display_id} Disconnected")

        except Exception as e:
            if DEBUG: print("Connection error:", e)
            poller.unregister(self.socket)
            try:
                del clients[self.socket]
            except Exception as e:
                if DEBUG: print("Client already deleted.")
            self.socket.close()
        
    def handle_write(self):
        if self._sendbuf != b'':
            if DEBUG: print("sending buffer")
            sent = self.socket.send(self._sendbuf)
            self._sendbuf = self._sendbuf[sent:]
        
READ_ONLY = ( select.POLLIN |
              select.POLLHUP |
              select.POLLERR )
READ_WRITE = READ_ONLY | select.POLLOUT

def update_display(display=None, state=0):
    if display is not None: 
        if DEBUG: print(f"updating display {display}")
        serve_number = 0
        if g.currently_serving == display:
            serve_number = g.current_serve       
        for dc in clients.values():
            if dc.display_id == display:
                dc.update(g.game_score[display], g.match_score[display], serve_number, state)
    else:
        # Call update individually on the displays..
        update_display(0)
        update_display(1)

def apply_state(display, state):
    if display is not None: 
        if DEBUG: print(f"updating display {display}")        
        serve_number = 0
        if g.currently_serving == display:
            serve_number = g.current_serve       
        for dc in clients.values():
            if dc.display_id == display:
                dc.update(g.game_score[display], g.match_score[display], serve_number, state)

def main():
    # Connect to network
    wifi = Wifi()
    wifi.disconnect()
    wifi.start_ap() 
    ip = wifi.wlan.ifconfig()[0]
    # ip = wifi.connect()
    
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((ip, SERVER_PORT))
    server_socket.listen()
    if DEBUG: print(f"Listening on {ip}:{SERVER_PORT}")
    server_socket.setblocking(False)
    poller.register(server_socket, select.POLLIN)    
    
    # START GAMEPLAY LOOP 
    
    buttons = [Button(14), Button(15)]
    buttons_pressed = [False, False]
    dual_timer = False
    
    while True:
        events = poller.poll(0)
        for sock, event in events:
            if sock is server_socket:
                client_socket, client_addr = server_socket.accept()
                if DEBUG: print("Client connected from", client_addr)
                client_socket.setblocking(False)
                poller.register(client_socket, READ_WRITE)
                clients[client_socket] = DisplayClient(client_socket)
            elif event & select.POLLIN:
                clients[sock].handle_read()
            elif event & select.POLLOUT:
                clients[sock].handle_write()     
        
         # update buttons
        for p in (0, 1):
            buttons_pressed[p] = buttons[p].is_pressed

        
        # Handle match and round starting
        if dual_timer:
            hold_timer = time.ticks_diff(time.ticks_ms(), dual_timer)
            if not all(buttons_pressed):
                if hold_timer > MATCH_HOLD_TIMER:                    
                    g.active_state = GameState.STARTING_MATCH
                    g.start_game()
                elif hold_timer > GAME_HOLD_TIMER:
                    g.active_state = GameState.STARTING_GAME
                    g.start_game()                
                dual_timer = False    
            continue    
        
        # Check for match start.        
        elif all(buttons_pressed):
            if DEBUG: print("Both pressed, initiating timer")
            dual_timer = time.ticks_ms()        
        
        if not g.active_state == GameState.STARTING_MATCH:            
            # Now we need to wait for both players to be released before we set the serve to false
            if g.active_state == GameState.STARTING_GAME and not any(buttons_pressed):                
                g.active_state = GameState.SELECTING
                update_display()
            
             # Handle who is serving on first round after both buttons are released again
            if g.active_state == GameState.SELECTING and not any(buttons_pressed):
                if DEBUG:print("Now waiting for input for who is going to serve")
                g.active_state = GameState.SERVING
                apply_state(0, 1)
                apply_state(1, 1)
                
            if g.active_state == GameState.SERVING and any(buttons_pressed):                
                pressed = buttons_pressed.index(True)
                if DEBUG: print(f"Player {pressed} will serve first")
                g.currently_serving = pressed
                g.active_state = GameState.WAITING
                
            if g.active_state == GameState.WAITING and not any(buttons_pressed):
                if DEBUG: print("starting game!")                
                g.active_state = GameState.IN_GAME
                update_display()
                
            # and now we move on to scoring!
            if g.active_state >= GameState.IN_GAME and g.active_state <= GameState.GAME_COMPLETE:                
                swap = False
                for p in (0, 1):
                    if buttons_pressed[p]:
                        swap = g.add_point(p)
                        if g.active_state == GameState.GAME_POINT:                        
                            apply_state(p, 2)
                        elif g.active_state == GameState.MATCH_POINT:
                            apply_state(p, 3)
                        update_display()
                        time.sleep(1)
                        break
                if swap:
                    if DEBUG: print("swapping sides")
                    buttons = list(reversed(buttons))
                    for c in clients.values():
                        c.display_id = 0 if c.display_id == 1 else 1
                    update_display()

if __name__ == "__main__":
    main()
    
