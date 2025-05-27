from datetime import datetime
import discord
from discord.ext import commands, tasks
from typing import Union
from database import get_async_session
from models import PrivateActionTypeENUM, PrivateRoom, PrivateRoomLog, PrivateRoomMember, TimeCounterLog, TimeParse, User, VoiceLogTypeENUM
from utils import get_embeds
from sqlalchemy import select

class MafiaCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        
        self.bot: discord.Bot = bot
        
        super().__init__()
    
    mafia_group = discord.SlashCommandGroup("mafia")
    
    @mafia_group.command(name="create")
    async def mafia_create_command(self, 
                                     ctx: discord.ApplicationContext):
        
        await ctx.defer(ephemeral=True)
        
        