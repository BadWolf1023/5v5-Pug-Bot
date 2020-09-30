'''
Created on Sep 15, 2020

@author: willg
'''
import discord
from typing import List
import aiohttp

lounge_mmr_api_url = 'https://mariokartboards.com/lounge/json/player.php?type=rt'

async def getJSONData(full_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(full_url) as r:
            if r.status == 200:
                js = await r.json()
                return js
            
def addFilter(url, filter_type, data):
    result = url
    result += "&" + filter_type + "="
    result += ",".join(data)
    #result = urllib.parse.quote(result)
    return result

    
def getMissingAPIPlayers(mmr_dict, data):
    data_names = set()
    for player_data in data:
        if 'name' in player_data:
            data_names.add(player_data['name'].lower())
    
    missing_players = {}
    for player in mmr_dict:
        if player not in data_names:
            missing_players[player] = mmr_dict[player]
            
    return missing_players

def getMissingPlayers(mmr_dict):
    missing = []
    for data in mmr_dict.values():
        if data[0] == -1:
            missing.append(data)
    return missing

def sort_by_mmr(mmr_dict):
    return sorted(mmr_dict.values(), key=lambda x: (x[0], x[1]), reverse=True)

def getTwoHighestMMRs(mmr_dict):
    sorted_by_mmr = sort_by_mmr(mmr_dict)
    return [sorted_by_mmr[0], sorted_by_mmr[1]]
        
        
async def getCaptains(mogi_players: List[discord.Member]):
    mmr_dict = {}
    lounge_names = []
    for player in mogi_players:
        lounge_lookup = player.display_name.replace(" ", "")
        mmr_dict[player.display_name.lower()] = (-1, lounge_lookup, player)
        lounge_names.append(lounge_lookup)
    
    fullURL = addFilter(lounge_mmr_api_url, "name", lounge_names)
    data = await getJSONData(fullURL)
    
    
    if data == None:
        print("Bad request to Lounge API... Data was None.")
        return None, None, None
    if "error" in data:
        print("Bad request to Lounge API... Error in data.")
        return None, None, None
    
    for player_data in data:
        if 'name' in player_data:
            mmr_dict_key = player_data['name'].lower()
            if mmr_dict_key in mmr_dict:
                if 'current_mmr' in player_data:
                    temp = mmr_dict[mmr_dict_key]
                    mmr_dict[mmr_dict_key] = (player_data['current_mmr'], temp[1], temp[2])
    
    
    all_players = sort_by_mmr(mmr_dict)
    captains = getTwoHighestMMRs(mmr_dict)
    missingPlayers = getMissingPlayers(mmr_dict)
    return captains, missingPlayers, all_players
    


