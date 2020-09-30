'''
Created on Sep 28, 2020

@author: willg
'''
import discord
import Shared
import copy
from typing import List
from datetime import datetime
from aiohttp.web_response import json_response

medium_delete = 10
long_delete = 30

mmr_lookup_terms = {"mmr"}
mmrlu_lookup_terms = {"mmrlu", "mmrlineup"}

runner_leaderboard_id = "341469667"
google_sheets_url_base = "https://sheets.googleapis.com/v4/spreadsheets/"
google_sheet_id = "1bvoJSerq9--gjSZhjT6COgU_fzQ20tnYikrwz6KwYw0"

google_api_key = None
google_sheet_gid_url = None


runner_leaderboard_name = "Runner Leaderboard"
bagger_leaderboard_name = "Bagger Leaderboard"

runner_mmr_range = "'" + runner_leaderboard_name + "'!C2:D"
bagger_mmr_range = "'" + bagger_leaderboard_name + "'!C2:D"

def addRanges(base_url, ranges):
    temp = copy.copy(base_url)
    for r in ranges:
        temp += "&ranges=" + r
    return temp
class MMR(object):

    def __init__(self):
        global google_sheet_gid_url
        google_sheet_gid_url = google_sheets_url_base + google_sheet_id + "/values:batchGet?" + "key=" + google_api_key
        self.last_mmr_pull = datetime.now()
        
    
    def is_mmr_check(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, mmr_lookup_terms, prefix)
    
    def mmr_data_is_corrupt(self, json_resp):
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
    
    def get_runner_mmr_list(self, json_resp): #No error handling - caller is responsible that the data is good
        return json_resp['valueRanges'][0]['values']
    def get_bagger_mmr_list(self, json_resp): #No error handling - caller is responsible that the data is good
        return json_resp['valueRanges'][1]['values']
        
    def get_mmr_for(self, names, mmr_list):
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
        
    def combine_and_sort_mmrs(self, runner_mmr_dict, bagger_mmr_dict): #caller has responsibility of making sure the keys for both dicts are the same
        if set(runner_mmr_dict.keys()) != set(bagger_mmr_dict.keys()):
            return {}
        
        mmr_dict = {}
        for lookup in runner_mmr_dict:
            mmr_dict[lookup] = runner_mmr_dict[lookup][0], runner_mmr_dict[lookup][1], bagger_mmr_dict[lookup][1]
        
        sorted_mmr = sorted(mmr_dict.values(), key=lambda p: (-p[1], -p[2], p[0])) #negatives are a hack way, so that in case of a tie, the names will be sorted alphabetically
        for ind, item in enumerate(sorted_mmr):
            if item[1] == -1:
                sorted_mmr[ind] = (sorted_mmr[ind][0], "Unknown", sorted_mmr[ind][2]) 
            if item[2] == -1:
                sorted_mmr[ind] = (sorted_mmr[ind][0], sorted_mmr[ind][1], "Unknown") 
        return sorted_mmr
    
    async def send_mmr(self, message:discord.Message):
        for_who = Shared.strip_prefix_and_command(message.content, mmr_lookup_terms)
        to_look_up = []
        if len(for_who) == 0: #get mmr for author
            to_look_up = [message.author.display_name]
        else: #they are trying to look someone, or multiple people up
            to_look_up = for_who.split(",")
            if len(to_look_up) > 15:
                message.channel.send("A maximum of 15 players can be checked at a time.", delete_after=medium_delete)
                return
            for name in to_look_up:
                if len(name) > 25:
                    message.channel.send("One of the names was too long. I'm not going to look this up.", delete_after=medium_delete)
                    return
        
        full_url = addRanges(google_sheet_gid_url, [runner_mmr_range, bagger_mmr_range])
        json_resp = await Shared.fetch(full_url)
        if self.mmr_data_is_corrupt(json_resp):
            message.channel.send("Could not pull mmr. Google Sheets isn't cooperating!", delete_after=medium_delete)
            return
        
        #At this point, we've verified that the data is not corrupt/bad
        #Let's send the list of runners and baggers to another function along with who we are looking up,
        #and they can return the mmr for each person looked up
        #Note that the function we give these lists to will still have to do some data integrity checking, but at least it won't be as bad
        
        runner_mmr = self.get_runner_mmr_list(json_resp)
        bagger_mmr = self.get_bagger_mmr_list(json_resp)
        results_runner = self.get_mmr_for(to_look_up, runner_mmr)
        results_bagger = self.get_mmr_for(to_look_up, bagger_mmr)
        combined_mmrs = self.combine_and_sort_mmrs(results_runner, results_bagger) 
        
        
        if len(combined_mmrs) == 0:
            return
        
        embed = discord.Embed(
                                title = "War Lounge MMR",
                                colour = discord.Colour.dark_blue()
                            )
        
        
        for name, runner_mmr, bagger_mmr in combined_mmrs:
            mmr_str = "R: " + str(runner_mmr) + " \u200b | \u200b B: " + str(bagger_mmr)
            embed.add_field(name=name, value=mmr_str, inline=False)
        
        
        await message.channel.send(embed=embed, delete_after=long_delete)
        
        
        
    async def mmr_handle(self, message:discord.Message):
        if not Shared.has_prefix(message.content):
            return False
        if self.is_mmr_check(message.content):
            await self.send_mmr(message)
            return True
        
        return False