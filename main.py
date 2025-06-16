import discord

from utils.config import DISCORD_BOT_TOKEN

class UbezhisheBot(discord.bot.Bot):
    
    pass
    
    
if __name__ == "__main__":
    
    bot = UbezhisheBot(owner_id=664752111933718538,
                       debug_guilds=[1307622842048839731],
                       intents=discord.Intents.all())
    
    def register_cogs():
        
        # TODO Заполнять Коги сюда
        from cogs.timecounter import TimeCounterCog
        from cogs.initial import InitialCog
        from cogs.rooms import RoomsCog
        from cogs.mafia import MafiaCog
        from cogs.bunker import BunkerCog
        
        for cog in [TimeCounterCog, InitialCog, RoomsCog, MafiaCog, BunkerCog]: bot.add_cog(cog(bot))
    
    
    
    
    
    
    
    
    
    register_cogs()
    
    bot.run(DISCORD_BOT_TOKEN)