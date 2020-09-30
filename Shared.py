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
from typing import List, Tuple, Set, Dict
import copy

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


RUNNER_MMR_MAXIMUMS = [(IRON_RUNNER,999),
                       (BRONZE_RUNNER,1999),
                       (SILVER_RUNNER,3999),
                       (GOLD_RUNNER,5999),
                       (PLATINUM_RUNNER,7999),
                       (DIAMOND_RUNNER,9999)
                      ]

BAGGER_MMR_MAXIMUMS = [(IRON_BAGGER,499),
                       (BRONZE_BAGGER,999),
                       (SILVER_BAGGER,1999),
                       (GOLD_BAGGER,2999),
                       (PLATINUM_BAGGER,3999),
                       (DIAMOND_BAGGER,4999)
                      ]

ROLE_ID_EMOGI_MAPPINGS = {
                IRON_RUNNER:"iron",
                BRONZE_RUNNER:"bronze",
                SILVER_RUNNER:"silver",
                GOLD_RUNNER:"gold",
                PLATINUM_RUNNER:"platinum",
                DIAMOND_RUNNER:"diamond",
                MASTER_RUNNER:"master",
                IRON_BAGGER:"iron",
                BRONZE_BAGGER:"bronze",
                SILVER_BAGGER:"silver",
                GOLD_BAGGER:"gold",
                PLATINUM_BAGGER:"platinum",
                DIAMOND_BAGGER:"diamond",
                MASTER_BAGGER:"master"
                }







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
update_role_terms = {"ur", "updaterole"}

google_sheets_url_base = "https://sheets.googleapis.com/v4/spreadsheets/"
google_sheet_id = "1bvoJSerq9--gjSZhjT6COgU_fzQ20tnYikrwz6KwYw0"

google_sheet_gid_url = None
google_api_key = None


runner_leaderboard_name = "Runner Leaderboard"
bagger_leaderboard_name = "Bagger Leaderboard"

runner_mmr_range = "'" + runner_leaderboard_name + "'!C2:D"
bagger_mmr_range = "'" + bagger_leaderboard_name + "'!C2:D"

can_update_role = {UPDATER_ID, DEVELOPER_ID, LOWER_TIER_ARBITRATOR_ID, HIGHER_TIER_ARBITRATOR_ID, BOSS_ID}
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

def addRanges(base_url, ranges):
    temp = copy.copy(base_url)
    for r in ranges:
        temp += "&ranges=" + r
    return temp
def get_emoji_by_name(emojis:List[discord.Emoji], name):
    for emoji in emojis:
        if emoji.name == name:
            return str(emoji)
    return name

def find_members_by_names(members:List[discord.Member], names:List[str], removeNone=False):
    names_edited = [name.lower().replace(" ", "") for name in names]
    found = [None] * len(names)
    for member in members:
        member_name = member.display_name.lower().replace(" ", "")
        if member_name in names_edited:
            name_index = names_edited.index(member_name)
            found[name_index] = member
    if removeNone:
        found = list(filter(lambda m: m != None, found))
    
    return found
            
        
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

def has_authority(author:discord.Member, valid_roles:set, admin_allowed=True):
    if admin_allowed:
        if author.guild_permissions.administrator:
            return True
        
    for role in author.roles:
        if role.id in valid_roles:
            return True
    return False 
    
def get_runner_role_ids(member_or_guild, role_objects_instead=False):
    temp = []
    for role in member_or_guild.roles:
        if role.id in RUNNER_ROLES:
            if role_objects_instead:
                temp.append(role)
            else:
                temp.append(role.id)
    return temp

def get_bagger_role_ids(member_or_guild, role_objects_instead=False):
    temp = []
    for role in member_or_guild.roles:
        if role.id in BAGGER_ROLES:
            if role_objects_instead:
                temp.append(role)
            else:
                temp.append(role.id)
    return temp


def get_role_mapping(role_ids:Set[int], guild:discord.guild):
    mappings = {}
    for role in guild.roles:
        if role.id in role_ids:
            mappings[role.id] = role
    if role_ids != set(mappings.keys()):
        return mappings, False
    return mappings, True
    


    
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


#returns runner and bagger mmr list from Google Sheets
    #Returns None,None is either data is corrupt
def get_mmr_for_names(names:List[str], mmr_list):
    to_send_back = {}
    for name in names:
        temp = name.replace(" ","").lower()
        if len(temp) == 0:
            continue
        if temp not in to_send_back:
            to_send_back[temp] = (name.strip(), -1)
    
    for lookup in to_send_back:
        for player_and_mmr in mmr_list:
            if not isinstance(player_and_mmr, list) or len(player_and_mmr) != 2\
                    or not isinstance(player_and_mmr[0], str) or not isinstance(player_and_mmr[1], str)\
                    or not player_and_mmr[1].isnumeric():
                break
            if lookup == player_and_mmr[0].replace(" ", "").lower():
                to_send_back[lookup] = (player_and_mmr[0].strip(), int(player_and_mmr[1]))
    return to_send_back

def get_mmr_for_members(members:List[discord.Member], mmr_list):
    to_send_back = {}
    for member in members:
        lookup = member.display_name.replace(" ","").lower()
        mmr = -1
        for player_and_mmr in mmr_list:
            if not isinstance(player_and_mmr, list) or len(player_and_mmr) != 2\
                    or not isinstance(player_and_mmr[0], str) or not isinstance(player_and_mmr[1], str)\
                    or not player_and_mmr[1].isnumeric():
                break
            if lookup == player_and_mmr[0].replace(" ", "").lower():
                mmr = int(player_and_mmr[1])
        to_send_back[hash(member)] = (member, mmr)
    return to_send_back

def get_runner_mmr_list(json_resp): #No error handling - caller is responsible that the data is good
        return json_resp['valueRanges'][0]['values']
def get_bagger_mmr_list(json_resp): #No error handling - caller is responsible that the data is good
    return json_resp['valueRanges'][1]['values']
    
def combine_mmrs(runner_mmr_dict, bagger_mmr_dict):
    if set(runner_mmr_dict.keys()) != set(bagger_mmr_dict.keys()):
        return {}
    mmr_dict = {}
    for lookup in runner_mmr_dict:
        mmr_dict[lookup] = runner_mmr_dict[lookup][0], runner_mmr_dict[lookup][1], bagger_mmr_dict[lookup][1]
    return mmr_dict

def mmr_data_is_corrupt(json_resp):
        if not isinstance(json_resp, dict): 
            return True
        #data integrity check #2
        if 'valueRanges' not in json_resp\
                    or not isinstance(json_resp['valueRanges'], list)\
                    or len(json_resp['valueRanges']) != 2:
            return True
            
        #data integrity check #3
        runner_leaderboard_dict = json_resp['valueRanges'][0]
        bagger_leaderboard_dict = json_resp['valueRanges'][1]
        if not isinstance(runner_leaderboard_dict, dict) or\
                    not isinstance(bagger_leaderboard_dict, dict) or\
                    'range' not in runner_leaderboard_dict or\
                    'range' not in bagger_leaderboard_dict or\
                    runner_leaderboard_name not in runner_leaderboard_dict['range'] or\
                    bagger_leaderboard_name not in bagger_leaderboard_dict['range'] or\
                    'values' not in runner_leaderboard_dict or\
                    'values' not in bagger_leaderboard_dict or\
                    not isinstance(runner_leaderboard_dict['values'], list) or\
                    not isinstance(bagger_leaderboard_dict['values'], list):
            return True
        return False
    
async def pull_all_mmr():
    full_url = addRanges(google_sheet_gid_url, [runner_mmr_range, bagger_mmr_range])
    json_resp = await fetch(full_url)
    if mmr_data_is_corrupt(json_resp):
        return None, None
    
    #At this point, we've verified that the data is not corrupt/bad
    #Let's send the list of runners and baggers to another function along with who we are looking up,
    #and they can return the mmr for each person looked up
    #Note that the function we give these lists to will still have to do some data integrity checking, but at least it won't be as bad
    
    runner_mmr = get_runner_mmr_list(json_resp)
    bagger_mmr = get_bagger_mmr_list(json_resp)
    return runner_mmr, bagger_mmr

def get_correct_roles_for_mmr(player:Tuple[discord.Member, int, int], role_mappings:Dict[int, discord.Role]):
    runner_role = None
    bagger_role = None
    running_mmr = player[1]
    bagging_mmr = player[2]
    if running_mmr != -1:
        for role_id, mmr_max in RUNNER_MMR_MAXIMUMS:
            runner_role = role_mappings[role_id]
            if running_mmr <= mmr_max:
                break
        else:
            runner_role = role_mappings[MASTER_RUNNER]
    if bagging_mmr != -1:
        for role_id, mmr_max in BAGGER_MMR_MAXIMUMS:
            
            bagger_role = role_mappings[role_id]
            if bagging_mmr <= mmr_max:
                break
        else:
            bagger_role = role_mappings[MASTER_BAGGER]
                
    return runner_role, bagger_role

def has_any_role_ids(member:discord.Member, role_ids:Set[int]):
    for role in member.roles:
        if role.id in role_ids:
            return True
    return False
    
def has_bagger_role(member:discord.Member):
    return has_any_role_ids(member, BAGGER_ROLES)
def has_runner_role(member:discord.Member):
    return has_any_role_ids(member, RUNNER_ROLES)

def get_role_changes(member_mmrs:Dict[int, Tuple[discord.Member, int, int]], role_mappings:Dict[int, discord.Role]):
    to_change = {}
    
    for member_hash, data in member_mmrs.items():
        runner_role, bagger_role = get_correct_roles_for_mmr(data, role_mappings)
        member = data[0]
        new_runner_role = None
        new_bagger_role = None
        if has_runner_role(member) and runner_role != None and runner_role not in member.roles:
            new_runner_role = runner_role
        if has_bagger_role(member) and bagger_role != None and bagger_role not in member.roles:
            new_bagger_role = bagger_role
        if new_runner_role != None or new_bagger_role != None:
            to_change[member_hash] = (member, new_runner_role, new_bagger_role)
        
    return to_change

async def process_changes(to_change:Dict[int, Tuple[discord.Member, discord.Role, discord.Role]], emojis:List[discord.Emoji]):
    str_msg = ""
    for member, new_runner_role, new_bagger_role in to_change.values():
        str_msg += member.mention + " "
        failed = False
        http_fail = False
        if new_runner_role != None:
            try:
                await member.remove_roles(*get_runner_role_ids(member, role_objects_instead=True), reason="MMR Change: Removing old running roles.")
                await member.add_roles(new_runner_role, reason="MMR Change: Giving new running role.")
            except discord.errors.Forbidden:
                failed = True
            except discord.errors.HTTPException:
                http_fail = True
            str_msg += get_emoji_by_name(emojis, ROLE_ID_EMOGI_MAPPINGS[new_runner_role.id]) + " Runner"
                
        if new_bagger_role != None:
            if new_runner_role != None:
                str_msg += ", "
            try:
                await member.remove_roles(*get_bagger_role_ids(member, role_objects_instead=True), reason="MMR Change: Removing old bagging roles.")
                await member.add_roles(new_bagger_role, reason="MMR Change: Giving new bagging role.")
            except discord.errors.Forbidden:
                failed = True
            except discord.errors.HTTPException:
                http_fail = True
            str_msg += get_emoji_by_name(emojis, ROLE_ID_EMOGI_MAPPINGS[new_bagger_role.id]) + " Bagger"
        
        if failed:
            str_msg += " - Failed to remove and/or add roles for this user. Maybe they are too far up the hierarchy."
        if http_fail:
            str_msg += " - Failed to remove and/or add roles for this user. Run again."
        
        str_msg += "\n"
    return str_msg

#============== PUG Bot Command Functions ==============

def is_add_fc_check(message:str, prefix=prefix):
    return is_in(message, add_fc_commands, prefix)
def is_get_fc_check(message:str, prefix=prefix):
    return is_in(message, get_fc_commands, prefix)
def is_update_role(message:str, prefix=prefix):
    return is_in(message, update_role_terms, prefix)
 
async def send_add_fc(message:discord.Message, valid_terms=add_fc_commands, prefix=prefix):
    str_msg = message.content
    str_msg = strip_prefix_and_command(str_msg, valid_terms, prefix)
    if len(str_msg) == 0:
        await message.channel.send("Provide an FC.", delete_after=medium_delete)
    elif _is_fc(str_msg):
        player_fcs[message.author.id] = str_msg
        await message.channel.send("FC has been set.", delete_after=medium_delete)
    elif _is_almost_fc(str_msg):
        player_fcs[message.author.id] = _fix_fc(str_msg)
        await message.channel.send("FC has been set.", delete_after=medium_delete)
    else:
        await message.channel.send("FC should be in the following format: ####-####-####", delete_after=medium_delete)

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
    elif is_update_role(message.content, prefix):
        if has_authority(message.author, can_update_role, admin_allowed=False):
            await message.delete()
            members = message.guild.members 
                    
            runner_mmr, bagger_mmr = await pull_all_mmr()
            if runner_mmr == None or bagger_mmr == None:
                await message.channel.send("Could not pull mmr. Google Sheets isn't cooperating!", delete_after=medium_delete)
                return
            runner_mmr_dict = get_mmr_for_members(members, runner_mmr)
            bagger_mmr_dict = get_mmr_for_members(members, bagger_mmr)
            combined = combine_mmrs(runner_mmr_dict, bagger_mmr_dict)
            
            
            mappings, success = get_role_mapping(set(RUNNER_ROLES | BAGGER_ROLES), message.guild)
            if not success:
                await message.channel.send("Could not map roles. No changes made. You should tell Bad Wolf that this happened this means his code has an error.")
                return
            to_be_changed = get_role_changes(combined, mappings)
            results = await process_changes(to_be_changed, message.guild.emojis)
            if len(results) != 0:
                await message.channel.send(results)
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
