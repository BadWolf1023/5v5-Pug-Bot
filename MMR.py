'''
Created on Sep 28, 2020

@author: willg
'''
import discord
import Shared
from datetime import datetime

medium_delete = 10
long_delete = 30

mmr_lookup_terms = {"mmr"}

runner_leaderboard_id = "341469667"
google_sheets_url_base = Shared.google_sheets_url_base
google_sheet_id = Shared.google_sheet_id

runner_leaderboard_name = Shared.runner_leaderboard_name
bagger_leaderboard_name = Shared.bagger_leaderboard_name




class MMR(object):

    def __init__(self):
        self.last_mmr_pull = datetime.now()
        
    
    def is_mmr_check(self, message:str, prefix:str=Shared.prefix):
        return Shared.is_in(message, mmr_lookup_terms, prefix)  
    
    
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
                
        runner_mmr, bagger_mmr = await Shared.pull_all_mmr()
        if runner_mmr == None or bagger_mmr == None:
            await message.channel.send("Could not pull mmr. Google Sheets isn't cooperating!", delete_after=medium_delete)
            return
        results_runner = Shared.get_mmr_for_names(to_look_up, runner_mmr)
        results_bagger = Shared.get_mmr_for_names(to_look_up, bagger_mmr)
        combined_mmrs = Shared.combine_and_sort_mmrs(results_runner, results_bagger) 
        
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
        elif message.content == "!runners":
            runner_list = []
            for member in message.guild.members:
                if Shared.has_runner_role(member):
                    runner_list.append((member.display_name, Shared.get_runner_role_ids(member, True)))
            
            runner_list.sort()
            print("Members with a runner role:\n")
            for runner in runner_list:
                print(runner[0] + "\t\t" + str(runner[1][0]))
        elif message.content == "!baggers":
            bagger_list = []
            for member in message.guild.members:
                if Shared.has_bagger_role(member):
                    bagger_list.append((member.display_name, Shared.get_bagger_role_ids(member, True)))
            
            bagger_list.sort()
            print("Members with a bagger role:\n")
            for bagger in bagger_list:
                print(bagger[0] + "\t\t" + str(bagger[1][0]))
        
        return False