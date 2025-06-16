import discord
from discord.ext import commands
from typing import Union
from utils.database import get_async_session
from utils.models import TimeCounterLog, User, VoiceLogTypeENUM
from sqlalchemy import select

class InitialCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        
        self.session = get_async_session()
        self.bot: discord.Bot = bot
        
        super().__init__()
    
    @commands.Cog.listener()
    async def on_ready(self):
        
        session = get_async_session()
        
        #  
        #  Создаём в базе данных всех пользователей
        #  
        
        guild: discord.Guild = await self.bot.fetch_guild(1307622842048839731)
        
        users = (await session.execute(select(User))).scalars().all()
        
        ids = [_.id for _ in users]
        
        async for member in guild.fetch_members(limit=150):
            
            if not ( member.id in ids ): session.add(User(id=member.id))
            
        await session.commit()
        
    