'''
Created on Sep 26, 2020

@author: willg
'''
import discord
import PlayerPicklable
from datetime import datetime, timedelta
warn_drop_period = timedelta(minutes=25)
drop_period = timedelta(minutes=30)

class Player(object):
    '''
    classdocs
    '''


    def __init__(self, member:discord.Member, runner=True):
        '''
        Constructor
        '''
        self.member = member
        self.runner = runner
        self.last_message_time = datetime.now()
        self.join_time = datetime.now()
        self.warned_already = False
        
    def reconstruct(self, pickle_player:PlayerPicklable, member:discord.Member):
        self.member = member
        self.runner = pickle_player.runner
        self.last_message_time = pickle_player.last_message_time
        self.join_time = pickle_player.join_time
        self.warned_already = pickle_player.warned_already
    
    def getPickablePlayer(self):
        return PlayerPicklable.PlayerPicklable(self.member.id, self.runner, self.last_message_time, self.join_time, self.warned_already)
        
    
    
    def get_join_time(self):
        return self.join_time
    
    def sent_message(self):
        self.last_message_time = datetime.now()
        self.warned_already = False
        
    def is_runner(self):
        return self.runner
    def is_bagger(self):
        return not self.runner
    
    def should_warn(self):
        time_passed = datetime.now() - self.last_message_time
        return time_passed >= warn_drop_period
    
    def should_drop(self):
        time_passed = datetime.now() - self.last_message_time
        return time_passed >= drop_period
        
        
        
    
        