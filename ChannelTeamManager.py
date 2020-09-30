'''
Created on Sep 14, 2020

@author: willg
'''
import discord
from datetime import datetime, timedelta
unlock_period = timedelta(minutes=3)


class ChannelTeamManager(object):
    '''
    classdocs
    '''


    def __init__(self, channel:discord.channel.TextChannel, captainA:discord.Member, captainB:discord.Member):
        self.mogi_started_at = datetime.now()
        self.is_locked = True
        self.channel = channel
        self.captainA = captainA
        self.captainB = captainB
        self.teamA = [self.captainA.display_name]
        self.teamB = [self.captainB.display_name]
        
    def is_overtime(self):
        time_passed = datetime.now() - self.mogi_started_at
        return time_passed >= unlock_period
            
            
    def should_be_unlocked(self):
        if not self.is_locked:
            return False
        if self.is_overtime():
            return True
        if self.teams_are_picked():
            return True
        return False
    
    def unlock(self):
        self.is_locked = False
    
    def pick(self, captain:discord.Member, player:str):
        if captain == self.captainA:
            self.addTeamA(player)
        elif captain == self.captainB:
            self.addTeamB(player)
        
    def addTeamA(self, player):
        self.teamA.append(player)
        
    def addTeamB(self, player):
        self.teamB.append(player)
    
    def teams_are_picked(self):
        return len(self.teamA) == 5 and len(self.teamB) == 5
    
    def repick(self):
        self.teamA = [self.captainA.display_name]
        self.teamB = [self.captainB.display_name]
    
    def getTeamsString(self):
        teams_str = "Team A: "
        for playerA in self.teamA:
            teams_str += playerA + ", "
        if teams_str.endswith(", "):
            teams_str = teams_str[:-2]
        
        teams_str += "\nTeam B: "
        for playerB in self.teamB:
            teams_str += playerB + ", "
            
        if teams_str.endswith(", "):
            teams_str = teams_str[:-2] 
        
        return teams_str  
    
    def isCaptain(self, member:discord.Member):
        return member == self.captainA or member == self.captainB