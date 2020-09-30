'''
Created on Sep 26, 2020

@author: willg
'''
import discord
import aiohttp
import dill as p
import os
from pathlib import Path
import shutil
from datetime import datetime
import re
from typing import List

prefix = "!"

REPORTER_ID = 751956336706846776
UPDATER_ID = 751956336706846778
DEVELOPER_ID = 751956336710779018
LOWER_TIER_ARBITRATOR_ID = 751956336719298567
HIGHER_TIER_ARBITRATOR_ID = 751956336719298568
BOSS_ID = 751956336719298569

IRON_RUNNER = 759444854182379570
BRONZE_RUNNER = 751956336643932167
SILVER_RUNNER = 751956336685744129
GOLD_RUNNER = 751956336685744132
PLATINUM_RUNNER = 751956336685744134
DIAMOND_RUNNER = 751956336685744136
MASTER_RUNNER = 751956336706846770

IRON_BAGGER = 759445071241150495
BRONZE_BAGGER = 753731888409215118
SILVER_BAGGER = 753731756028330115
GOLD_BAGGER = 753731578009485442
PLATINUM_BAGGER = 753731124697628901
DIAMOND_BAGGER = 753730690893349064
MASTER_BAGGER = 754142296257069124

RUNNER_NAMES = {IRON_RUNNER:"Iron Runner",
                BRONZE_RUNNER:"Bronze Runner",
                SILVER_RUNNER:"Silver Runner",
                GOLD_RUNNER:"Gold Runner",
                PLATINUM_RUNNER:"Platinum Runner",
                DIAMOND_RUNNER:"Diamond Runner",
                MASTER_RUNNER:"Master Runner"}
RUNNER_ROLES = set(RUNNER_NAMES.keys())

BAGGER_NAMES = {IRON_BAGGER:"Iron Bagger",
                BRONZE_BAGGER:"Bronze Bagger",
                SILVER_BAGGER:"Silver Bagger",
                GOLD_BAGGER:"Gold Bagger",
                PLATINUM_BAGGER:"Platinum Bagger",
                DIAMOND_BAGGER:"Diamond Bagger",
                MASTER_BAGGER:"Master Bagger"}
BAGGER_ROLES = set(BAGGER_NAMES.keys())



allowed_runner_tiers = {1:(IRON_RUNNER,),
                        2:(IRON_RUNNER, BRONZE_RUNNER),
                        3:(BRONZE_RUNNER, SILVER_RUNNER),
                        4:(SILVER_RUNNER, GOLD_RUNNER),
                        5:(GOLD_RUNNER,PLATINUM_RUNNER),
                        6:(PLATINUM_RUNNER, DIAMOND_RUNNER, MASTER_RUNNER),
                        7:(DIAMOND_RUNNER, MASTER_RUNNER)}

allowed_bagger_tiers = {1:(IRON_BAGGER,),
                        2:(IRON_BAGGER, BRONZE_BAGGER),
                        3:(BRONZE_BAGGER, SILVER_BAGGER),
                        4:(SILVER_BAGGER, GOLD_BAGGER),
                        5:(GOLD_BAGGER,PLATINUM_BAGGER),
                        6:(PLATINUM_BAGGER, DIAMOND_BAGGER, MASTER_BAGGER),
                        7:(DIAMOND_BAGGER, MASTER_BAGGER)}

backup_folder = "backups/"
player_fc_pickle_path = "player_fcs.pkl"
backup_file_list = [player_fc_pickle_path]
add_fc_commands = {"setfc"}
get_fc_commands = {"fc"}
#Need here to avoid circular import...
ml_terms = {"ml","mogilist"}
mllu_terms = {"mllu","mogilistlineup"}
player_fcs = {}
medium_delete = 7

def has_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    return message.startswith(prefix)

def strip_prefix(message:str, prefix:str=prefix):
    message = message.strip()
    if message.startswith(prefix):
        return message[len(prefix):]
    
def is_in(message:str, valid_terms:set, prefix:str=prefix):
    if (has_prefix(message, prefix)):
        message = strip_prefix(message, prefix).strip()
        args = message.split()
        if len(args) == 0:
            return False
        return args[0].lower().strip() in valid_terms
            
    return False

def find_member_by_str(members:List[discord.Member], name:str):
    name = name.lower().replace(" ", "")
    for member in members:
        if name == member.display_name.lower().replace(" ", ""):
            return member
    return None
    

def strip_prefix_and_command(message:str, valid_terms:set, prefix:str=prefix):
    message = strip_prefix(message, prefix)
    args = message.split()
    if len(args) == 0:
        return message
    if args[0].lower().strip() in valid_terms:
        message = message[len(args[0].lower().strip()):]
    return message.strip()

def is_boss(member:discord.Member):
    return BOSS_ID in member.roles
    
def get_runner_role_ids(author:discord.Member):
    temp = []
    for role in author.roles:
        if role.id in RUNNER_ROLES:
            temp.append(role.id)
    return temp

def get_bagger_role_ids(author:discord.Member):
    temp = []
    for role in author.roles:
        if role.id in BAGGER_ROLES:
            temp.append(role.id)
    return temp
    
def get_tier_number(channel:discord.channel.TextChannel):
    numbers = [val for val in channel.name if val.isnumeric()]
    if len(numbers) == 0:
        return None
    return int("".join(numbers))

def can_run_in_tier(member:discord.Member, tier_number:int):
    if tier_number == None or tier_number not in allowed_runner_tiers.keys():
        return False
    
    if is_boss(member):
        return True
    
    member_runner_roles = get_runner_role_ids(member)
    if len(member_runner_roles) == 0:
        return False
    allowed_runner_roles = allowed_runner_tiers[tier_number]
    for member_runner_role in member_runner_roles:
        if member_runner_role in allowed_runner_roles:
            return True
    return False

def can_bag_in_tier(member:discord.Member, tier_number:int):
    if tier_number == None or tier_number not in allowed_bagger_tiers.keys():
        return False
    
    if is_boss(member):
        return True
    
    member_bagger_roles = get_bagger_role_ids(member)
    if len(member_bagger_roles) == 0:
        return False
    allowed_bagger_roles = allowed_bagger_tiers[tier_number]
    for member_bagger_role in member_bagger_roles:
        if member_bagger_role in allowed_bagger_roles:
            return True
    return False

def get_required_runner_role_names(tierNumber:int):
    if tierNumber == None or tierNumber not in allowed_runner_tiers.keys():
        return []
    return [RUNNER_NAMES[runner_role] for runner_role in allowed_runner_tiers[tierNumber]]

def get_required_bagger_role_names(tierNumber:int):
    if tierNumber == None or tierNumber not in allowed_bagger_tiers.keys():
        return []
    return [BAGGER_NAMES[bagger_role] for bagger_role in allowed_bagger_tiers[tierNumber]]


def _is_fc(fc):
    return re.match("^[0-9]{4}[-][0-9]{4}[-][0-9]{4}$", fc.strip()) != None

def _is_almost_fc(fc):
    fc = fc.replace(" ", "")
    return re.match("^[0-9]{12}$", fc.strip()) != None

#No out of bounds checking is done - caller is responsible for ensuring that the FC is 12 numbers, only being separated by spaces
def _fix_fc(fc):
    fc = fc.replace(" ", "")
    return fc[0:4] + "-" + fc[4:8] + "-" + fc[8:12]

#============== PUG Bot Command Functions ==============

def is_add_fc_check(message:str, prefix=prefix):
    return is_in(message, add_fc_commands, prefix)
def is_get_fc_check(message:str, prefix=prefix):
    return is_in(message, get_fc_commands, prefix)

async def send_add_fc(message:discord.Message, valid_terms=add_fc_commands, prefix=prefix):
    str_msg = message.content
    str_msg = strip_prefix_and_command(str_msg, valid_terms, prefix)
    if len(str_msg) == 0:
        await message.channel.send("Provide an FC.", delete_after=medium_delete)
        return
    elif _is_fc(str_msg):
        player_fcs[message.author.id] = str_msg
        await message.channel.send("FC has been set.", delete_after=medium_delete)
        return
    elif _is_almost_fc(str_msg):
        player_fcs[message.author.id] = _fix_fc(str_msg)
        await message.channel.send("FC has been set.", delete_after=medium_delete)
        return
    else:
        await message.channel.send("FC should be in the following format: ####-####-####", delete_after=medium_delete)
        return

async def send_fc(message:discord.Message, valid_terms=get_fc_commands, prefix=prefix):
    str_msg = message.content
    str_msg = strip_prefix_and_command(str_msg, valid_terms, prefix)
    if len(str_msg) == 0: #getting author's fc
        if message.author.id in player_fcs:
            await message.channel.send(player_fcs[message.author.id])
        else:
            await message.channel.send("You have not set an FC. Do: " + prefix + "setfc ####-####-####", delete_after=medium_delete)
    else:
        player_name = str_msg
        member = find_member_by_str(message.guild.members, player_name)
        if member == None:
            await message.channel.send("No one in this server has that name.", delete_after=medium_delete)
        else:
            if member.id in player_fcs:
                await message.channel.send(player_fcs[member.id])
            else:
                await message.channel.send(member.display_name + " doesn't have an fc set.", delete_after=medium_delete)
        
    
    
async def process_other_command(message:discord.Message, prefix=prefix):
    if not has_prefix(message.content, prefix):
        return False
    if is_add_fc_check(message.content, prefix):
        await send_add_fc(message, prefix=prefix)
    elif is_get_fc_check(message.content, prefix):
        await send_fc(message, prefix=prefix)
    else:
        return False
    return True


def is_ml(message:str, prefix:str=prefix):
    return is_in(message, ml_terms, prefix)

def is_mllu(message:str, prefix:str=prefix):
    return is_in(message, mllu_terms, prefix)

    

#============== Synchronous HTTPS Functions ==============
async def fetch(url, headers=None):
    async with aiohttp.ClientSession() as session:
        if headers == None:
            async with session.get(url) as response:
                return await response.json()
        else:
            async with session.get(url, headers=headers) as response:
                return await response.json()



#============== PICKLES AND BACKUPS ==============         
def initialize():
    load_player_fc_pickle()

def check_create(file_name):
    if not os.path.isfile(file_name):
        f = open(file_name, "w")
        f.close()
  
def backup_files(to_back_up=backup_file_list):
    Path(backup_folder).mkdir(parents=True, exist_ok=True)
    todays_backup_path = backup_folder + str(datetime.date(datetime.now())) + "/"
    Path(todays_backup_path).mkdir(parents=True, exist_ok=True)
    for file_name in to_back_up:
        try:
            if not os.path.exists(file_name):
                continue
            temp_file_n = file_name
            if os.path.exists(todays_backup_path + temp_file_n):
                for i in range(50):
                    temp_file_n = file_name + "_" + str(i) 
                    if not os.path.exists(todays_backup_path + temp_file_n):
                        break
            shutil.copy2(file_name, todays_backup_path + temp_file_n)
        except Exception as e:
            print(e)
            
#backs up the current pickle - does not dump the dictionary to the pickle; use player_fc_pickle_dump for that
def backup_player_fc_pickle():
    backup_files([player_fc_pickle_path])
    
def load_player_fc_pickle():
    global player_fcs
    player_fcs = {}
    if os.path.exists(player_fc_pickle_path):
        with open(player_fc_pickle_path, "rb") as pickle_in:
            try:
                player_fcs = p.load(pickle_in)
            except:
                print("Could not read in pickle for player fcs.")
                raise
    
    

def player_fc_pickle_dump():
    with open(player_fc_pickle_path, "wb") as pickle_out:
        try:
            p.dump(player_fcs, pickle_out)
        except:
            print("Could not dump pickle for player fcs.")
            raise
