import os
import discord

from utils.config import DISCORD_BOT_TOKEN

class UbezhisheBot(discord.bot.Bot):
    
    pass
    
    
if __name__ == "__main__":
    
    bot = UbezhisheBot(owner_id=664752111933718538,
                       debug_guilds=[1307622842048839731],
                       intents=discord.Intents.all())
    
    def register_cogs():
        
        cogs_list = [_[:-3] for _ in os.listdir("./cogs") if _.endswith(".py")]

        for cog in cogs_list:
            bot.load_extension(f'cogs.{cog}')
    
    
    
    
    
    register_cogs()
    
    bot.run(DISCORD_BOT_TOKEN)