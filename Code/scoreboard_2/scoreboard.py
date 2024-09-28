import math
import time
import random

from settings import *

FRAME_TIME = 66
STATE_WAITING = 1
STATE_GAME_POINT = 2
STATE_MATCH_POINT = 3
STATE_NO_NETWORK = 4
STATE_WAITING_START = 5

ticks_ms = None
ticks_diff = None

try:
    ticks_diff = time.ticks_diff
    ticks_ms = time.ticks_ms
except AttributeError:
    ticks_diff = lambda x, y: x - y
    ticks_ms = lambda: round(time.time() * 1000)

def rjust(s, length, char):
    while len(s) < length:
        s = char + s
    return s

_char_map = {
        "_": [0, 1, 0, 0, 0, 0, 0],
        " ": [0, 0, 0, 0, 0, 0, 0],
        "0": [1, 1, 1, 1, 1, 1, 0],
        "1": [0, 0, 1, 1, 0, 0, 0],
        "2": [1, 1, 0, 1, 1, 0, 1],
        "3": [0, 1, 1, 1, 1, 0, 1],
        "4": [0, 0, 1, 1, 0, 1, 1],
        "5": [0, 1, 1, 0, 1, 1, 1],
        "6": [1, 1, 1, 0, 1, 1, 1],
        "7": [0, 0, 1, 1, 1, 0, 0],
        "8": [1, 1, 1, 1, 1, 1, 1],
        "9": [0, 1, 1, 1, 1, 1, 1],

        # Optional?
        "A": [1, 0, 1, 1, 1, 1, 1],
        "b": [1, 1, 1, 0, 0, 1, 1],
        "C": [1, 1, 0, 0, 1, 1, 0],
        "c": [1, 1, 0, 0, 0, 0, 1],
        "d": [1, 1, 1, 1, 0, 0, 1],
        "E": [1, 1, 0, 0, 1, 1, 1],
        "F": [1, 0, 0, 0, 1, 1, 1],
        "G": [1, 1, 1, 0, 1, 1, 0],
        "h": [1, 0, 1, 0, 0, 1, 1],
        "J": [1, 1, 1, 1, 0, 0, 0],
        "L": [1, 1, 0, 0, 0, 1, 0],
        "n": [1, 0, 1, 0, 0, 0, 1],
        "o": [1, 1, 1, 0, 0, 0, 1],
        "P": [1, 0, 0, 1, 1, 1, 1],
        "r": [1, 0, 0, 0, 0, 0, 1],
        "t": [1, 1, 0, 0, 0, 1, 1],
        "U": [1, 1, 1, 1, 0, 1, 0],
        "u": [1, 1, 1, 0, 0, 0, 0],
        "-": [0, 0, 0, 0, 0, 0, 1],
    }
    

def _repeating_color(color):
    while True:
        yield color
        
def apply_brightness(color):
    return (int(color[0] * BRIGHTNESS), int(color[1] * BRIGHTNESS), int(color[2] * BRIGHTNESS))

class SevenSegmentArray:   
    def __init__(self, np, length=2, px_per_segment=10, offset=0, color=SCORE_COLORS[SCOREBOARD_NUMBER]):
        self.px_per_segment = px_per_segment
        self.np = np
        self.length = length
        self.offset = offset
        self.value = self._value_to_raw("  ")
        self.color = apply_brightness(color)
        self.flashing = False
        self.spinning = False
        
    def set(self, value, color=None):
        if color is not None:
            color = apply_brightness(color)
        self.set_raw(self._value_to_raw(value), color=color)

    def _value_to_raw(self, value):
        value = rjust(str(value)[:self.length], self.length, " ")
        result = []
        for c in range(self.length):
            cmap = _char_map.get(value[c], _char_map["_"])
            result.extend(cmap)
        print(f"value to raw '{value}'->'{result}' ({self.length})")
        return result    
        
    def set_raw(self, value, color=None):        
        if color:
            if hasattr(color, "__next__"):
                colors = color
            elif len(color) == 3 and isinstance(color[0], int):
                colors =  _repeating_color(color)
            else:
                colors = color
        else:
            colors = _repeating_color(self.color)
                
        self.value = value
        for seg_idx, seg_on in enumerate(value):
            for p in range(self.px_per_segment):
                self.np[self.offset + (seg_idx * self.px_per_segment + p)] = next(colors) if seg_on else (0, 0, 0)

    def pixel_count(self):
        return self.length * 7 * self.px_per_segment
    
    def _spin_colors(self, color, position, length):
        tail_len = int(length / 2)
        for i in range(length):
            if i == position:
                yield color
            elif (position - i) % length < tail_len:
                b = 1-((position - i) % length) / tail_len
                yield (int(color[0] * b), int(color[1] * b), int(color[2] * b))
            else:
                yield (0, 0, 0)
            
    def tick(self, ms):
        if self.flashing:
            brightness = (1+math.sin(ms / 500)) * 0.5 
            color = (int(self.color[0] * brightness), int(self.color[1] * brightness), int(self.color[2] * brightness))
            self.set_raw(self.value, color=color)
        elif self.spinning:
            t = ms % 1000
            active_pixels = sum(self.value) * self.px_per_segment
            pos = int(active_pixels * (t / 1000.0))
            self.set_raw(self.value, color=self._spin_colors(self.color, pos, active_pixels))
            
class ServeIndicator:
    def __init__(self, np, length=2, px_per_segment=2, offset=0, color=SCORE_COLORS[SCOREBOARD_NUMBER]):
        self.np = np
        self.px_per_segment = px_per_segment
        self.length = length
        self.offset = offset
        self.value = 0
        self.color = apply_brightness(color)

    def pixel_count(self):
        return self.length * self.px_per_segment

    def set(self, serve, color=None):
        if color:
            self.color = color
        self.value = serve
        cutoff = self.offset + serve * self.px_per_segment        
        for i in range(self.offset, self.offset + self.length * self.px_per_segment):
            self.np[i] = self.color if i < cutoff else (0, 0, 0)


class Scoreboard:
    def __init__(self, np, score_px_per_segment=10, match_px_per_segment=6, px_per_serve_indicator=2):
        self.np = np
        self._score_disp = SevenSegmentArray(np, length=2, px_per_segment=score_px_per_segment, color=SCORE_COLORS[SCOREBOARD_NUMBER])
        self.set_score(88)
        self._match_disp = SevenSegmentArray(np, length=1, px_per_segment=match_px_per_segment, offset=self._score_disp.pixel_count(), color=MATCH_COLORS[SCOREBOARD_NUMBER])
        self.set_match_score(8)
        self._serve_disp = ServeIndicator(np, length=2, px_per_segment=px_per_serve_indicator, offset=self._score_disp.pixel_count() + self._match_disp.pixel_count(), color=SERVE_COLOR)
        self.set_serve(SCOREBOARD_NUMBER + 1)
        self._score_disp.flashing = True
        self._match_disp.spinning = True
        self._last_tick = 0
        self._ticks = 0        

    def set_score(self, score, color=None, update=False):
        self._score_disp.set(score, color=color)
        if update:
            self.update()

    def set_match_score(self, score, color=None, update=False):
        self._match_disp.set(score, color=color)
        if update:
            self.update()
    
    def set_serve(self, serve, color=None, update=False):
        self._serve_disp.set(serve, color=color)
        if update:
            self.update()

    def tick(self, ms):
        if ticks_diff(ms, self._last_tick) > FRAME_TIME:
            self._score_disp.tick(ms)
            self._match_disp.tick(ms)
            self._last_tick = ms
            self._ticks += 1
            self.update()
            
    def handle_update(self, scoreboard_number, score, match, serve, state):
        self._score_disp.spinning = False
        self._score_disp.color = apply_brightness(SCORE_COLORS[scoreboard_number])
        self._score_disp.flashing = False
        self._match_disp.spinning = False
        self._match_disp.color = apply_brightness(MATCH_COLORS[scoreboard_number])
        self._match_disp.flashing = False
        
        if state == STATE_WAITING:
            self._score_disp.set("00")
            self._score_disp.color = apply_brightness(SPIN_COLOR)
            self._score_disp.spinning = True
            self._match_disp.set(match)
            self._match_disp.spinning = True
            self._serve_disp.set(serve)
            self._serve_disp.flashing = True
        elif state == STATE_GAME_POINT:            
            self._score_disp.set(score)
            self._score_disp.flashing = True
            self._match_disp.set(match)
            self._serve_disp.set(serve)
        elif state == STATE_MATCH_POINT:
            self._score_disp.set(score)
            self._score_disp.flashing = True
            self._match_disp.set(match)
            self._match_disp.spinning = True
            self._serve_disp.set(serve)
        elif state == STATE_NO_NETWORK:
            self._score_disp.set(score)
            self._score_disp.flashing = True
            self._match_disp.set(match)
            self._match_disp.flashing = True
        elif state == STATE_WAITING_START:
            self._score_disp.set(score)
            self._score_disp.flashing = True
            self._match_disp.set(match)
            self._match_disp.flashing = True
            self._serve_disp.set(serve)
            self._serve_disp.flashing = True
        else:                    
            self._score_disp.set(score)            
            self._match_disp.set(match)
            self._serve_disp.set(serve)
        """
        if state in (WIN, LOSE):
            self._score_disp.flashing = True
            self._score_disp.color = apply_brightness((0, 255, 0)) if state == WIN else apply_brightness((255, 0, 0))
            self._match_disp.flashing = True
            self._match_disp.color = apply_brightness((0, 255, 0)) if state == WIN else apply_brightness((255, 0, 0))
            self._score_disp.set(score)
            self._match_disp.set(match)
            self._serve_disp.set(serve)

        elif state in (HOLD_GAME, HOLD_MATCH):
            self._score_disp.spinning = True            
            self._score_disp.color = apply_brightness((0, 0, 255)) if state == HOLD_GAME else apply_brightness((0, 255, 255))
            self._score_disp.set("00")
        
        else:
            self._score_disp.color = apply_brightness((196, 64, 0))
            self._match_disp.color = apply_brightness((255, 0, 0))
            self._score_disp.set(score)
            self._match_disp.set(match)
            self._serve_disp.set(serve)
        """
        self.update()

    def update(self):
        self.np.write()
