from settings import *


class GameState:
    STARTING_MATCH = 0
    STARTING_GAME = 1
    SELECTING = 2
    SERVING = 3
    WAITING = 4
    IN_GAME = 5
    GAME_POINT = 6
    MATCH_POINT = 7
    GAME_COMPLETE = 100
    MATCH_COMPLETE = 1000

class Game:
    def __init__(self):
        self.game_score = [0, 0]
        self.match_score = [0, 0]
        self.active_state = GameState.STARTING_MATCH
        self.current_serve = 0
        self.currently_serving = None    
    
    def add_point(self, pnum):
        other_pnum = 1 if pnum == 0 else 0
        # Add point and see if it is game over or not.
        self.game_score[pnum] += 1        
        if self.game_score[pnum] >= 11 and self.game_score[pnum] >= self.game_score[other_pnum] + 2:            
            return self.game_complete()
            
        # check for game / match point.
        if self.game_score[pnum] >= 10 and self.game_score[pnum] < 9:
            self.state = GameState.GAME_POINT
            if self.match_score[pnum] == 3:
                self.state == GameState.MATCH_POINT                
        # Switch serves every 2, until 20, then every time.
        if self.current_serve == 2 or self.get_total_score() >= 20:
            self.current_serve = 1
            self.switch_server()
        else:
            self.current_serve += 1
        self.print_status()        
        #TODO: Update scoreboards with all the new data.

    def game_complete(self):
        if DEBUG: print("game complete")
        winning_pnum = 0
        losing_pnum = 1
        if self.game_score[1] > self.game_score[0]:
            winning_pnum = 1
            losing_pnum = 0
        self.match_score[winning_pnum] += 1
        if self.match_score[winning_pnum] == 4:
            self.active_state = GameState.MATCH_COMPLETE
        else:
            self.active_state = GameState.GAME_COMPLETE
            self.start_game(server=losing_pnum)  # This is winning_pnum to accomodate table rotation at the end of the round,
            return True # True = swap sides
    
    def get_total_score(self):
        return self.game_score[0] + self.game_score[1]
    
    def print_status(self):            
        if DEBUG: print("{}({}) - {}({})    Serving: {}".format(
            self.game_score[0], self.match_score[0], self.game_score[1], self.match_score[1], self.currently_serving))
    
    def start_game(self, server=None):   
        self.game_score = [0, 0]    
        self.current_serve = 1
        if self.active_state == GameState.STARTING_GAME or self.active_state == GameState.STARTING_MATCH:
            if DEBUG: print("Starting new match / game.")
            if self.active_state == GameState.STARTING_MATCH:
                self.match_score = [0, 0]                            
            self.active_state = GameState.SELECTING
            
        if self.active_state == GameState.GAME_COMPLETE and server is not None:
            if DEBUG: print("Starting next game.")
            self.currently_serving = server
            self.active_state = GameState.IN_GAME
            
        self.print_status()
        
    def switch_server(self):        
        self.currently_serving = 1 if self.currently_serving == 0 else 0
        if DEBUG: print(f"Changing serve to: {self.currently_serving}")
