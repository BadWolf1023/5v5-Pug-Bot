'''
Created on Sep 14, 2020

@author: willg
'''

import discord
from discord.utils import get
from typing import List, Tuple
from discord.ext import tasks

import TierMogi
import Player
import Shared
import os
import dill as p
import sys
import atexit
import signal
import MMR

import ChannelTeamManager
import MMRPull
bot_key = None
testing_bot_key = None
pickle_dump_path = "tiers_pickle.pkl"
private_info_file = "private.txt"

pug_lounge_server_id = 751956336593338441
ECHELON_CATEGORY = 751956338912788559
BOT_TESTING_CATEGORY = 755258711605510185
MODERATION_CATEGORY = 751956338116001843
allowed_mogi_categories = [ECHELON_CATEGORY, BOT_TESTING_CATEGORY, MODERATION_CATEGORY]
#mogi_bot_id = 450127943012712448
DEBUGGING = False

tier_mogi_instances = {}
mmr_channel_instances = {}
tier_instances = {}
client = discord.Client()




async def create_captain_role(channel:discord.channel.TextChannel):
    try:
        channel_captain_role = await channel.guild.create_role(name=channel.name + "-captain")
        await channel.set_permissions(channel_captain_role, send_messages=True)
        return channel_captain_role
    except discord.Forbidden:
        await channel.send("Could not create captain role. Missing permissions.")
    

async def delete_captain_role(channel:discord.channel.TextChannel):
    role = discord.utils.get(channel.guild.roles, name=channel.name + "-captain")

    while role:
        try:
            await role.delete()
        except discord.Forbidden:
            await channel.send("Could not remove captain role. Missing permissions.")
            break
        except discord.errors.NotFound:
            break
            pass
        role = discord.utils.get(channel.guild.roles, name=channel.name + "-captain")

async def get_channels_captain_role(channel:discord.channel.TextChannel):
    return get(channel.guild.roles, name=channel.name + "-captain")

async def get_captains(message:discord.Message):
    return await MMRPull.getCaptains(message.mentions)
    
async def assign_captains_roles(message:discord.Message, captains:List[discord.Member], captain_role:discord.Role):
    try:
        for captain in captains:
            await captain.add_roles(captain_role)
    except discord.Forbidden:
        await message.channel.send("Could not assign captains their roles. Missing permissions.")


async def unlock_captains(channel:discord.channel.TextChannel):
    await channel.set_permissions(channel.guild.default_role, read_messages=False, send_messages=None)
    await delete_captain_role(channel) 
    
"""def new_mogi(message:discord.Message):
    return message.author.id == mogi_bot_id and "has started a mogi" in message.content
def mogi_started(message:discord.Message):
    return message.author.id == mogi_bot_id and "Type `!list` to get a list of the players (once every 30 seconds)" in message.content
"""

def create_channel_team_manager(channel:discord.channel.TextChannel, capA:discord.Member, capB:discord.Member):
    return ChannelTeamManager.ChannelTeamManager(channel, capA, capB)

def create_mmr_string(players:List[Tuple[int, str, discord.Member]]):
    mmr_str = "**Player List**"
    for index, player in enumerate(players, 1):
        mmr_str += "\n`" + str(index) + ".` "
        mmr_str += player[2].display_name + " (MMR: "
        if player[0] == -1:
            mmr_str += "NAN - Name doesn't match Lounge name"
        else:
            mmr_str += str(player[0])
        mmr_str += ")"
    return mmr_str

@client.event
async def on_message(message: discord.Message):
    #mkwxSoup, roomID, rLID = await roomExistsLoop(roomID)
    ##########################################################################################At this point, we know the room exists, and we certainly have rLID. We're not sure if we have the roomID yet though.    
    #ignore everything outside of 5v5 Lounge
    if message.guild == None:
        return
    #ignore your own messages
    if message.author == client.user:
        return
    if message.guild.id != pug_lounge_server_id:
        return
    
    channel_id = message.channel.id
    
    if message.channel.category_id in allowed_mogi_categories or\
    Shared.is_ml(message.content) or Shared.is_mllu(message.content):
        if message.channel.id not in tier_mogi_instances:
            tier_mogi_instances[channel_id] = TierMogi.TierMogi(message.channel)
        tier_mogi = tier_mogi_instances[channel_id]
        was_mogi_command = await tier_mogi.sent_message(message, tier_mogi_instances.values())
        if was_mogi_command:
            return
    
    if not Shared.has_prefix(message.content, Shared.prefix):
        return
    
    if channel_id not in mmr_channel_instances:
        mmr_channel_instances[channel_id] = MMR.MMR()
    channel_mmr = mmr_channel_instances[channel_id]
    was_mmr_command = await channel_mmr.mmr_handle(message)
    if was_mmr_command:
        return
    
    
    was_other_command = await Shared.process_other_command(message)
    if was_other_command:
        return
    
    
    #if mogi bot is saying something, it might be useful
    """if message.author.id == mogi_bot_id:
        if mogi_started(message):
            await message.channel.send("Chat is locked down while captains pick teams.")
            await message.channel.set_permissions(message.channel.guild.default_role, read_messages=False, send_messages=False)
            captain_role = await create_captain_role(message.channel)
            if captain_role != None:
                captains, _, allPlayers = await get_captains(message)
                captains_member_list = [c[2] for c in captains]
                
                if len(captains) != 2:
                    await message.channel.send("Did not have 2 captains. Unlocking chat. Pick teams manually.")
                    await unlock_captains(message.channel)
                    return
                await assign_captains_roles(message, captains_member_list, captain_role)
                
                tier_instances[message.channel.id] = create_channel_team_manager(message.channel, captains_member_list[0], captains_member_list[1])
                mmr_str = create_mmr_string(allPlayers)
                await message.channel.send(captains_member_list[0].mention + " and " + captains_member_list[1].mention + \
                                           ", you have 3 minutes to pick teams.\nTo select someone to be on your team, use the prefix " + prefix + " and then their name." + \
                                           " Only pick one person at a time.\nExample: " + prefix + "Rob\n\nIf you need to repick teams, do: `" + prefix + "repick`" +\
                                           "\n\n" + mmr_str)

        elif new_mogi(message):
            time.sleep(.5)
            try:
                await message.channel.fetch_message(message.id)
                last_sent = message.channel.last_message
                #To avoid the mogi bot bug where it double sends on !esn, we'll check if the last message sent was our own reset
                if last_sent != None and last_sent.author == client.user and "New mogi started. Teams have been reset." in last_sent.content:
                    pass
                else:
                    await message.channel.send("New mogi started. Teams have been reset.")
                    if message.channel.id in tier_instances:
                        del tier_instances[message.channel.id]
                    await unlock_captains(message.channel)
            except discord.errors.NotFound:
                pass
                
            
    else:
        channel_id = message.channel.id
        if message.content.startswith(prefix):
            new_message = strip_prefix(message.content, prefix).strip()
            
            if channel_id in tier_instances and tier_instances[channel_id].is_locked:
                ctm = tier_instances[channel_id]
                if ctm.isCaptain(message.author):
                    if new_message.strip().lower() in ['restart', 'repick']:
                        ctm.repick()
                        await message.channel.send("Done. Pick the teams again.\n" + ctm.getTeamsString())
                    elif new_message.strip().lower() in ['esn']:
                        pass
                    else:
                        ctm.pick(message.author, discord.utils.escape_markdown(discord.utils.escape_mentions(new_message)))
                        if ctm.teams_are_picked():
                            ctm.unlock()
                            await unlock_captains(ctm.channel)
                            await message.channel.send("The teams have been chosen. The chat is now unlocked.\n\n" + ctm.getTeamsString())
                        else:
                            await message.channel.send(ctm.getTeamsString())
                
            if new_message.lower() in ['teams', 'team']:
                if channel_id in tier_instances:
                    ctm = tier_instances[channel_id]
                    team_str = ctm.getTeamsString()
                    delete_me = await message.channel.send(team_str)
                    await delete_me.delete(delay=20)
                else:
                    delete_me = await message.channel.send("No mogi going on currently.")
                    await delete_me.delete(delay=5)
        
                    
    """                
                    
                
        
"""@tasks.loop(seconds=30)
async def unlockCheck():
    for ctm in tier_instances.values():
        if ctm.should_be_unlocked():
            ctm.unlock()
            await unlock_captains(ctm.channel)
            await ctm.channel.send("The captains took too long to pick the teams. Channel unlocked. Pick teams manually.")
"""     
@tasks.loop(seconds=45)
async def routine_tier_checks():
    for tier_mogi in tier_mogi_instances.values():
        await tier_mogi.drop_warn_check()
        
@tasks.loop(hours=24)
async def backup_player_fcs():
    Shared.player_fc_pickle_dump()
    Shared.backup_player_fc_pickle()
        
       
       
def get_channel(channels, channel_id):
    temp = discord.utils.get(channels, id=channel_id)
    return temp
def get_member(members, member_id):
    temp = discord.utils.get(members, id=member_id)
    return temp

def private_data_init():
    global testing_bot_key
    global bot_key
    with open(private_info_file, "r") as f:
        testing_bot_key = f.readline().strip("\n")
        bot_key = f.readline().strip("\n")
        MMR.google_api_key = f.readline().strip("\n")

@client.event
async def on_ready():
    """global user_flag_exceptions
    unlockCheck.start()"""
    global tier_mogi_instances
    if os.path.exists(pickle_dump_path):
        guild = client.get_guild(pug_lounge_server_id)
        members = guild.members
        channels = guild.text_channels
        picklable_dict = {}
        with open(pickle_dump_path, "rb") as pickle_in:
            try:
                picklable_dict = p.load(pickle_in)
            except:
                print("Could not read tier instances in.")
                picklable_dict = {}
                raise
            
        new_tier_instances = {}
        for channel_id, picklable_tier_mogi in picklable_dict.items():
            cur_channel = get_channel(channels, picklable_tier_mogi.channel_id)
            if cur_channel == None:
                continue
            
            mogi_list = []
            player_error = False
            for picklable_player in picklable_tier_mogi.mogi_list:
                curPlayer = Player.Player(None, None)
                curMember = get_member(members, picklable_player.member_id)
                if curMember == None:
                    player_error = True
                else:
                    curPlayer.reconstruct(picklable_player, curMember)
                    mogi_list.append(curPlayer)
            curTier = TierMogi.TierMogi(None)
            curTier.reconstruct(mogi_list, cur_channel, picklable_tier_mogi)
            if player_error:
                curTier.recalculate()
            new_tier_instances[channel_id] = curTier
            
        tier_mogi_instances = new_tier_instances
    
    Shared.backup_player_fc_pickle()
    Shared.load_player_fc_pickle()
        
    routine_tier_checks.start()
    backup_player_fcs.start()
    


def on_exit():
    print("Exiting...")
    global tier_mogi_instances
    global pickle_dump_path
    
    with open(pickle_dump_path, "wb") as pickle_out:
        try:
            mogis = {}
            for channel_id, mogi in tier_mogi_instances.items():
                mogis[channel_id] = mogi.getPicklableTierMogi()
            p.dump(mogis, pickle_out)
        except:
            print("Could not dump pickle for tier instances.")
            Shared.player_fc_pickle_dump()
            raise
        
    Shared.player_fc_pickle_dump()

def handler(signum, frame):
    sys.exit()

signal.signal(signal.SIGINT, handler)

atexit.register(on_exit)

private_data_init()
client.run(bot_key)
