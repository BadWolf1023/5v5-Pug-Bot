'''
Created on Sep 26, 2020

@author: willg
'''
import discord
import Player
import Shared
from _datetime import timedelta
from datetime import datetime
import TierMogiPicklable
from typing import List

DEFAULT_MOGI_SIZE = 10
MAX_SUBS = 5
DEFAULT_RUNNER_SIZE = 8
DEFAULT_BAGGER_SIZE = 2
canning_terms = {"c","can"}
bagging_terms = {"b", "bag", "canbag", "cb"}
dropping_terms = {"d","drop"}
drop_all_terms = {"da","dropall"}
esn_terms = {"esn", "endstartnext"}
list_terms = {"l", "s", "list"}
remove_terms = {"r", "remove"}
ping_terms = {"p", "h", "here", "mention", "m"}
ml_terms = Shared.ml_terms
mllu_terms = Shared.mllu_terms
set_host_terms = {"sethost", "sh"}
get_host_terms = {"host"}

QUEUE_ERRORS = {0:"success", 1:"is already in the mogi", 2:"cannot play in this tier", 3:"mogi alread has max type", 4:"mogi is completely full", 5:"switched roles"}

REPORTER_ID = Shared.REPORTER_ID
UPDATER_ID = Shared.UPDATER_ID
DEVELOPER_ID = Shared.DEVELOPER_ID
LOWER_TIER_ARBITRATOR_ID = Shared.LOWER_TIER_ARBITRATOR_ID
HIGHER_TIER_ARBITRATOR_ID = Shared.HIGHER_TIER_ARBITRATOR_ID
BOSS_ID = Shared.BOSS_ID

can_ping = {REPORTER_ID, UPDATER_ID, DEVELOPER_ID, LOWER_TIER_ARBITRATOR_ID, HIGHER_TIER_ARBITRATOR_ID, BOSS_ID}
can_remove = {REPORTER_ID, UPDATER_ID, DEVELOPER_ID, LOWER_TIER_ARBITRATOR_ID, HIGHER_TIER_ARBITRATOR_ID, BOSS_ID}
can_esn = {UPDATER_ID, DEVELOPER_ID, LOWER_TIER_ARBITRATOR_ID, HIGHER_TIER_ARBITRATOR_ID, BOSS_ID}

LIST_WAIT_TIME = timedelta(seconds=20)
ESN_WAIT_TIME = timedelta(minutes=40)
PING_INTERVAL = timedelta(minutes=10)
ML_WAIT_TIME = timedelta(seconds=15)
MLLU_WAIT_TIME = timedelta(seconds=45)
quick_delete = 5
medium_delete = 5
long_delete = 30

class TierMogi(object):

    def __init__(self, channel:discord.channel.TextChannel):
        '''
        Constructor
        '''
        self.initialize(channel)
    
    def initialize(self, channel:discord.channel.TextChannel):
        self.mogi_list = []
        self.channel = channel
        self.last_list_time = None
        self.last_ml_time = None
        self.last_mllu_time = None
        self.start_time = None
        self.last_ping_time = None
        self.bagger_count = 0
        self.runner_count = 0
        self.host = None
    
    def getPicklableTierMogi(self):
        temp = [p.getPickablePlayer() for p in self.mogi_list]
        return TierMogiPicklable.TierMogiPicklable(temp,
                                                   self.channel.id,
                                                   self.last_list_time,
                                                   self.last_ml_time,
                                                   self.last_mllu_time,
                                                   self.start_time,
                                                   self.last_ping_time,
                                                   self.bagger_count,
                                                   self.runner_count,
                                                   self.host)
        
    def reconstruct(self, mogi_list:List[Player.Player],
                    channel:discord.channel.TextChannel,
                    picklableTierMogi:TierMogiPicklable.TierMogiPicklable):
        self.mogi_list = mogi_list
        self.channel = channel
        self.last_list_time = picklableTierMogi.last_list_time
        self.last_ml_time = picklableTierMogi.last_ml_time
        self.last_mllu_time = picklableTierMogi.last_mllu_time
        self.start_time = picklableTierMogi.start_time
        self.last_ping_time = picklableTierMogi.last_ping_time
        self.bagger_count = picklableTierMogi.bagger_count
        self.runner_count = picklableTierMogi.runner_count
        if 'host' in picklableTierMogi.__dict__:
            self.host = picklableTierMogi.host
        else:
            self.host = None
        
    
    def recalculate(self):
        self.sort_by_join_time()
        self.bagger_count = sum(1 for p in self.mogi_list if p.is_bagger())
        self.runner_count = sum(1 for p in self.mogi_list if p.is_runner())
        
    def sort_by_join_time(self):
        self.mogi_list.sort(key=lambda p: p.get_join_time())
        
    def addMember(self, player:Player.Player):
        self.mogi_list.append(player)
        self.sort_by_join_time()
    
    """def addMembers(self, otherMogi):
        self.mogi_list(otherMogi.mogi_list)
        self.sort_by_join_time()
    """ 
    def moveMembers(self, otherMogi):
        self.addMembers(otherMogi)
        otherMogi.reset()
        
    def reset(self):
        self.initialize(self.channel)
    
    def isFull(self):
        return len(self.mogi_list) >= DEFAULT_MOGI_SIZE
    def hasHalfOrMore(self):
        return len(self.mogi_list) >= int(DEFAULT_MOGI_SIZE/2)
    
    def countRunners(self):
        return self.runner_count
    
    def countBaggers(self):
        return self.bagger_count
    
    def get_warn_drop_list(self):
        warn_list = []
        for player in self.mogi_list:
            if player.should_warn() and not player.warned_already:
                warn_list.append(player)
        return warn_list
               
    def get_drop_list(self):
        drop_list = []
        for player in self.mogi_list:
            if player.should_drop():
                drop_list.append(player)
        return drop_list
    
    async def warn_drop(self):
        to_warn = self.get_warn_drop_list()
        if len(to_warn) == 0:
            return
        
        str_msg = ""
        for player in to_warn:
            player.warned_already = True
            str_msg += player.member.mention + ", "
        str_msg = str_msg[:-2]
        str_msg += " type something in the chat in the next 5 minutes to stay in the mogi"
        await self.channel.send(str_msg, delete_after=300)
    
    async def drop_inactive(self):
        to_drop = self.get_drop_list()
        if len(to_drop) < 1:
            return
        
        str_msg = ""
        for player in to_drop:
            self.mogi_list.remove(player)
            if player.is_runner():
                self.runner_count -= 1
            else:
                self.bagger_count -= 1
            str_msg += player.member.mention + ", "
        str_msg = str_msg[:-2]
        str_msg += " has been removed from the mogi due to inactivity"
        await self.channel.send(str_msg, delete_after=60)
    
    def is_can(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, canning_terms, prefix)

    def is_bag(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, bagging_terms, prefix)
    
    def is_drop(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, dropping_terms, prefix)
    
    def is_drop_all(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, drop_all_terms, prefix)
     
    def is_list(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, list_terms, prefix)
    
    def is_esn(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, esn_terms, prefix)
    
    def is_remove(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, remove_terms, prefix)
    
    def is_ping(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, ping_terms, prefix)
    
    def is_ml(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, ml_terms, prefix)
    
    def is_mllu(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, mllu_terms, prefix)
    
    def is_set_host(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, set_host_terms, prefix)
    
    def is_get_host(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, get_host_terms, prefix)
    
    
    
    def has_authority(self, author:discord.Member, valid_roles:set, admin_allowed=True):
        if admin_allowed:
            if author.guild_permissions.administrator:
                return True
            
        for role in author.roles:
            if role.id in valid_roles:
                return True
        return False 
        
    def can_ping(self, author:discord.Member):
        if self.isFull() or not self.hasHalfOrMore():
            return False
        return self.has_authority(author, can_ping)
    def can_esn(self, author:discord.Member):
        if self.start_time != None:
            time_passed = datetime.now() - self.start_time
            if time_passed >= ESN_WAIT_TIME:
                return True
        return self.has_authority(author, can_esn)
    def can_remove(self, author:discord.Member):
        return self.has_authority(author, can_remove)
    

    def can_send_list(self):
        if self.last_list_time == None:
            return True
        time_passed = datetime.now() - self.last_list_time
        return time_passed >= LIST_WAIT_TIME
    def can_send_ml(self):
        if self.last_ml_time == None:
            return True
        time_passed = datetime.now() - self.last_ml_time
        return time_passed >= ML_WAIT_TIME
    
    def can_send_mllu(self):
        if self.last_mllu_time == None:
            return True
        time_passed = datetime.now() - self.last_mllu_time
        return time_passed >= MLLU_WAIT_TIME
    
    def can_set_host(self):
        return self.start_time != None
    
    def get_mmr_str(self, double_line=True):
        mmr_str = ""
        if double_line:
            mmr_str += "\n\n"
        mmr_str += "`^mmr "
        for player in self.mogi_list:
            mmr_str += player.member.display_name + ", "
        if mmr_str[-2] == ",":
            return mmr_str[:-2] + "`"
        return ""
    
    def can(self, member:discord.Member):
        player = self.get(member)
        if player == None:
            player = Player.Player(member, runner=True)
            self.addMember(player)
        else:
            player.runner = True
        
    def bag(self, member:discord.Member):
        player = self.get(member)
        if player == None: #new player joined
            player = Player.Player(member, runner=False)
            self.addMember(player)
        else:
            player.runner = False
            
                
            
    def can_drop(self, member:discord.Member): 
        if not self.isFull():
            return True
        for player in self.mogi_list[:DEFAULT_MOGI_SIZE]:
            if player.member == member:
                return False
        return True
    
    def drop(self, member:discord.Member):
        for ind, player in enumerate(self.mogi_list):
            if player.member == member:
                dropped = self.mogi_list.pop(ind)
                if dropped.is_bagger():
                    self.bagger_count -= 1
                else:
                    self.runner_count -= 1
                return dropped
            
    def drop_all(self, member:discord.Member, mogis):
        success_drop = 0
        failed_drop = 0
        for mogi in mogis:
            if member in mogi:
                if mogi.can_drop(member):
                    success_drop += 1
                    mogi.drop(member)
                else:
                    failed_drop += 1
        return success_drop, failed_drop
        
        
        
    def __contains__(self, member):
        
        if isinstance(member, discord.Member):
            for player in self.mogi_list:
                if player.member == member:
                    return True
        elif isinstance(member, Player.Player):
            return member in self.mogi_list
        
        return False
    
    def get(self, member):
        if isinstance(member, discord.Member):
            for player in self.mogi_list:
                if player.member == member:
                    return player
        if isinstance(member, discord.Member):
            for player in self.mogi_list:
                if player == member:
                    return player
        return None
    
    def __update__(self, member):
        if isinstance(member, discord.Member):
            for player in self.mogi_list:
                if player.member == member:
                    player.sent_message()
        elif isinstance(member, Player.Player):
            member.sent_message()
        
            
    #Sending message functions
    async def send_esn(self, message:discord.Message):
        self.last_ping_time = datetime.now()
        await message.channel.send(message.author.display_name + " has started a mogi -- @here `!can` or `!bag` if not playing")
    
    
    async def send_remove(self, message:discord.Message, removed:discord.Member):
        await message.channel.send(removed.display_name + " has been removed from the mogi.")
    
    async def send_set_host(self, message:discord.Message):
        if message.author.id not in Shared.player_fcs:
            await message.channel.send("You have not set an FC. Do " + Shared.prefix + "setfc ####-####-#### first.", delete_after=Shared.medium_delete)
        else:
            self.host = Shared.player_fcs[message.author.id]
            await message.channel.send("Host set.", delete_after=medium_delete)
    async def send_host(self, message:discord.Message):
        if self.start_time == None:
            await message.channel.send("There is no host. The mogi has not filled yet.", delete_after=medium_delete)
        elif self.host == None:
            await message.channel.send("No one has set host yet.")
        else:
            await message.channel.send(self.host)
            
    async def send_ping(self, message:discord.Message):
        self.last_ping_time = datetime.now()
        msg_str = "@here "
        needed_baggers = DEFAULT_BAGGER_SIZE - self.bagger_count
        needed_runners = DEFAULT_RUNNER_SIZE - self.runner_count
        if needed_runners >= 1:
            msg_str += "+" + str(needed_runners) + " runner"
            if needed_runners > 1:
                msg_str += "s"
            msg_str += ", "
            
        if needed_baggers >= 1:                
            msg_str += "+" + str(needed_baggers) + " bagger"
            if needed_baggers > 1:
                msg_str += "s"
            msg_str += " "
        
        if msg_str[-2] == ",":
            msg_str = msg_str[:-2]
    
        await message.channel.send(msg_str)
    async def send_list(self, message:discord.Message, show_mmr=True):
        if len(self.mogi_list) == 0:
            await message.channel.send("There are no players in the mogi")
        else:
            list_str = "`Mogi List`"
            for list_num, player in enumerate(self.mogi_list, 1):
                list_str += "\n`" + str(list_num) + ".` " + player.member.display_name
                if player.is_bagger():
                    list_str += " (bagger)"
            list_str += "\n\nYou can type `!list` again in " + str(int(LIST_WAIT_TIME.total_seconds())) + " seconds."
            self.last_list_time = datetime.now()
            if show_mmr:
                list_str += self.get_mmr_str(double_line=True)
            await message.channel.send(list_str)
    
    async def send_ml(self, message:discord.Message, active_mogis, include_players=False):
        if include_players:
            self.last_mllu_time = datetime.now()
        else:
            self.last_ml_time = datetime.now()
        if active_mogis == None or len(active_mogis) == 0:
            await message.channel.send("There are no active mogis")
            return
        
        temp = sorted(active_mogis, key=lambda mogi:mogi.channel.name)
        mogis = []
        active_mogis = 0
        full_mogis = 0
        for mogi in temp:
            if mogi.mogi_list != None and len(mogi.mogi_list) != 0:
                mogis.append(mogi)
                active_mogis += 1
                if mogi.isFull():
                    full_mogis += 1
                
        
        if active_mogis == 0:
            await message.channel.send("There are no active mogis")
            return

        msg_str = ""
        if active_mogis == 1:
            msg_str += "There is " + str(active_mogis) + " active mogi and "
        else:
            msg_str += "There are " + str(active_mogis) + " active mogis and "
        
        if full_mogis == 1:
            msg_str += str(full_mogis) + " full mogi"
        else:
            msg_str += str(full_mogis) + " full mogis"
        
        msg_str += "\n"
        
        for mogi in mogis:
            msg_str += "\n" + mogi.channel.mention + " - " + str(len(mogi.mogi_list)) + "/10"
            if include_players:
                msg_str += "\n"
                for player in mogi.mogi_list:
                    msg_str += player.member.display_name + ", "
                msg_str = msg_str[:-2]
        if not include_players:
            msg_str += "\n\nTo get the line up for each mogi, type `!mogilistlineup` or `!mllu`"
            await message.channel.send(msg_str, delete_after=int(ML_WAIT_TIME.total_seconds()))
        else:
            await message.channel.send(msg_str, delete_after=int(MLLU_WAIT_TIME.total_seconds()))
    
    def can_can(self, message:discord.message):
        player = self.get(message.author)
        tier_number = Shared.get_tier_number(message.channel)
        if player == None: #They are joining as a new player
            if self.isFull():
                if len(self.mogi_list) >= DEFAULT_MOGI_SIZE + MAX_SUBS:
                    return 4
                else:
                    if Shared.can_run_in_tier(message.author, tier_number):
                        return 0
                    else:
                        return 2
            elif self.countRunners() == DEFAULT_RUNNER_SIZE:
                return 3
            else:
                if Shared.can_run_in_tier(message.author, tier_number):
                    return 0
                else:
                    return 2

        elif player.is_runner():
            return 1
        else:
            if self.countRunners() == DEFAULT_RUNNER_SIZE:
                return 3
            elif Shared.can_run_in_tier(message.author, tier_number):
                return 5
            else:
                return 2
        
    def can_bag(self, message:discord.message):
        player = self.get(message.author)
        tier_number = Shared.get_tier_number(message.channel)
        if player == None: #They are joining as a new player
            if self.isFull():
                if len(self.mogi_list) >= DEFAULT_MOGI_SIZE + MAX_SUBS:
                    return 4
                else:
                    if Shared.can_bag_in_tier(message.author, tier_number):
                        return 0
                    else:
                        return 2
            elif self.countBaggers() >= DEFAULT_BAGGER_SIZE:
                return 3
            else:
                if Shared.can_bag_in_tier(message.author, tier_number):
                    return 0
                else:
                    return 2
        elif player.is_bagger():
            return 1
        else:
            if self.countBaggers() >= DEFAULT_BAGGER_SIZE:
                return 3
            elif Shared.can_bag_in_tier(message.author, tier_number):
                return 5
            else:
                return 2
    
    
    def removeFromAllExceptFull(self, member:discord.Member, all_mogis):
        removed = []
        for mogi in all_mogis:
            if mogi.channel != self.channel and member in mogi and mogi.can_drop(member):
                mogi.drop(member)
                removed.append((mogi.channel,member))
        return removed
    
    async def send_removed_because_full(self, channels_removed_players:dict):
        for all_dropped in channels_removed_players.values():
            if len(all_dropped) == 0:
                continue
            msg_str = ""
            channel = all_dropped[0][0]
            for _, removed_member in all_dropped:
                msg_str += removed_member.display_name + ", "
            msg_str = msg_str[:-2]
            
            if len(all_dropped) == 1:
                msg_str += " has"
            else:
                msg_str += " have"
            msg_str += " been removed from this mogi because " + self.channel.name + " is full"
            await channel.send(msg_str, delete_after=long_delete)
                
            
    async def process_mogi_start(self, all_mogis, show_mmr=True):
        if len(self.mogi_list) == DEFAULT_MOGI_SIZE:
            self.start_time = datetime.now()
            str_msg = ""
            removed = []
            for player in self.mogi_list:
                str_msg += player.member.mention + " "
                temp = self.removeFromAllExceptFull(player.member, all_mogis)
                if len(temp) > 0:
                    removed.append(temp)
                
            to_send = {}
            for player_removed_channels in removed:
                for (removed_channel, member) in player_removed_channels:
                    if removed_channel.id not in to_send:
                        to_send[removed_channel.id] = []
                    to_send[removed_channel.id].append((removed_channel, member))
            await self.send_removed_because_full(to_send)
                
                
            str_msg += "\n\nThere are 10 players in the mogi. Captains, begin selecting teams."
            if show_mmr:
                str_msg += self.get_mmr_str(double_line=True)
            await self.channel.send(str_msg)
     
                        
    async def send_can_message(self, message:discord.Message, error_code=0):
        if error_code == 0:
            await message.channel.send(message.author.display_name + " has joined the mogi as a runner", delete_after=quick_delete)
        elif error_code == 1:
            await message.channel.send(message.author.display_name + " is already in the mogi as a runner", delete_after=quick_delete)
        elif error_code == 2:
            msg_str = message.author.display_name + " cannot run in this tier"
            required_role_names = Shared.get_required_runner_role_names(Shared.get_tier_number(self.channel))
            if required_role_names != None and len(required_role_names) > 0:
                msg_str += " - must be "
                for role_name in required_role_names:
                    msg_str += role_name + " or "
                msg_str = msg_str [:-4]
            await message.channel.send(msg_str, delete_after=quick_delete)
        elif error_code == 3:
            await message.channel.send(message.author.display_name + " cannot join the mogi because it already has " + str(DEFAULT_RUNNER_SIZE) + " runners", delete_after=quick_delete)
        elif error_code == 4:
            await message.channel.send(message.author.display_name + " cannot join the mogi because it is completely full", delete_after=quick_delete)
        elif error_code == 5:
            await message.channel.send(message.author.display_name + " has changed to a runner", delete_after=quick_delete)
    
    async def send_bag_message(self, message:discord.Message, error_code=0):
        if error_code == 0:
            await message.channel.send(message.author.display_name + " has joined the mogi as a bagger", delete_after=quick_delete)
        elif error_code == 1:
            await message.channel.send(message.author.display_name + " is already in the mogi as a bagger", delete_after=quick_delete)
        elif error_code == 2:
            msg_str = message.author.display_name + " cannot bag in this tier"
            required_role_names = Shared.get_required_bagger_role_names(Shared.get_tier_number(self.channel))
            if required_role_names != None and len(required_role_names) > 0:
                msg_str += " - must be "
                for role_name in required_role_names:
                    msg_str += role_name + " or "
                msg_str = msg_str [:-4]
            await message.channel.send(msg_str, delete_after=quick_delete)
        elif error_code == 3:
            await message.channel.send(message.author.display_name + " cannot join the mogi because it already has " + str(DEFAULT_BAGGER_SIZE) + " baggers", delete_after=quick_delete)
        elif error_code == 4:
            await message.channel.send(message.author.display_name + " cannot join the mogi because it is completely full", delete_after=quick_delete)
        elif error_code == 5:
            await message.channel.send(message.author.display_name + " has changed to a bagger", delete_after=quick_delete)

            
    async def send_drop(self, message:discord.Message, was_full=False):
        if message.author not in self:
            await message.channel.send(message.author.display_name + " is already dropped from the mogi", delete_after=quick_delete)
        elif was_full:
            await message.channel.send(message.author.display_name + " cannot drop from the mogi because it is full", delete_after=quick_delete)
        else:
            await message.channel.send(message.author.display_name + " dropped from the mogi", delete_after=quick_delete)
   
    async def send_drop_all(self, message:discord.Message, success_drop, failed_drop):
        total_mogis = success_drop + failed_drop
        if failed_drop == 0:
            if success_drop == 1:
                await message.channel.send(message.author.display_name + " dropped from 1 out of 1 mogi", delete_after=medium_delete)
            else:
                await message.channel.send(message.author.display_name + " dropped from " + str(success_drop) + " out of " + str(total_mogis) + " mogis", delete_after=medium_delete)
        else:
            if success_drop == 1:
                await message.channel.send(message.author.display_name + " dropped from 1 mogi, could not drop from " + str(failed_drop) + " mogi because it is full", delete_after=medium_delete)
            else:
                await message.channel.send(message.author.display_name + " dropped from " + str(success_drop) + " mogis, could not drop from " + str(failed_drop) + " mogi because it is full", delete_after=medium_delete)
        
    async def drop_warn_check(self):
        if self.start_time == None:
            await self.warn_drop()
            await self.drop_inactive()
    
    def should_ping(self):
        if self.isFull():
            return False
        if self.hasHalfOrMore():
            if self.last_ping_time == None:
                return True
            else:
                time_passed = datetime.now() - self.last_ping_time
                if (time_passed >= PING_INTERVAL):
                    return True
        return False
            
    async def sent_message(self, message:discord.Message, all_mogis=None):
        self.__update__(message.author)
        message_str = message.content
        if self.is_can(message_str):
            can_error_code = self.can_can(message)
            
            if can_error_code == 5:
                self.runner_count += 1
                self.bagger_count -= 1
            elif can_error_code == 0:
                self.runner_count += 1
                
            await self.send_can_message(message, can_error_code)
            if can_error_code == 0 or can_error_code == 5:
                self.can(message.author)
                if self.should_ping():
                    await self.send_ping(message)
                await self.process_mogi_start(all_mogis)
                
        elif self.is_bag(message_str):
            can_bag_error_code = self.can_bag(message)
            if can_bag_error_code == 5:
                self.bagger_count += 1
                self.runner_count -= 1
            elif can_bag_error_code == 0:
                self.bagger_count += 1
                
            await self.send_bag_message(message, can_bag_error_code)
            if can_bag_error_code == 0 or can_bag_error_code == 5:
                self.bag(message.author)
                if self.should_ping():
                    await self.send_ping(message)
                await self.process_mogi_start(all_mogis)
            
        elif self.is_drop(message_str):
            if self.can_drop(message.author):
                await self.send_drop(message)
                self.drop(message.author)
            else:
                await self.send_drop(message, was_full=True)
                
        elif self.is_drop_all(message_str):
            dropped, failedDrop = self.drop_all(message.author, all_mogis)
            await self.send_drop_all(message, dropped, failedDrop)
                
                
        elif self.is_esn(message_str):
            if self.can_esn(message.author):
                await self.send_esn(message)
                self.reset()
            else:
                await message.channel.send(message.author.display_name + " does not have permission to end this mogi", delete_after=medium_delete)
        
        elif self.is_remove(message_str):
            if self.can_remove(message.author):
                args = Shared.strip_prefix(message_str).split()
                if len(args) >= 1 and args[1].strip().isnumeric():
                    remove_number = int(args[1].strip())
                    if len(self.mogi_list) >= remove_number and remove_number > 0:
                        removedPlayer = self.drop(self.mogi_list[remove_number-1].member)
                        await self.send_remove(message, removedPlayer.member)
                        
        
        elif self.is_ping(message_str):
            if self.can_ping(message.author):
                await message.delete()
                await self.send_ping(message)
                
        elif self.is_list(message_str):
            if self.can_send_list():
                await self.send_list(message)
        
        elif self.is_ml(message_str):
            if self.can_send_ml():
                await self.send_ml(message, all_mogis, include_players=False)
                
        elif self.is_mllu(message_str):
            if self.can_send_mllu():
                await self.send_ml(message, all_mogis, include_players=True)
        
        elif self.is_set_host(message_str):
            if self.can_set_host():
                await self.send_set_host(message)
            else:
                await message.channel.send("You can only set host after the mogi has started.", delete_after=medium_delete)
        elif self.is_get_host(message_str):
            await self.send_host(message)
        else:
            return False
        
        return True
        