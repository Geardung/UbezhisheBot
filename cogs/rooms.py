from datetime import datetime
import discord
from discord.ext import commands, tasks
from typing import Union
from database import get_async_session
from models import PrivateRoom, PrivateRoomMember, TimeCounterLog, TimeParse, User, VoiceLogTypeENUM
from utils import get_embeds
from sqlalchemy import select

PRIVATE_CATEGORY = 1331257581255131167 # Категория где все войсы
CREATE_PRIVATE_ROOM = 1331265751788818433 # Войс для создания приватки

class CreateRoomView(discord.ui.View):
    
    def __init__(self, timeout = None, disable_on_timeout: bool = False):
        super().__init__(timeout=timeout, 
                         disable_on_timeout=disable_on_timeout)
        
class RoomsCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        
        self.bot: discord.Bot = bot
        
        self.session = get_async_session()
        
        super().__init__()
    
    @commands.Cog.listener()
    async def on_ready(self):
        
        category: discord.CategoryChannel = await self.bot.fetch_channel(PRIVATE_CATEGORY)
        
        for chnl in category.voice_channels:
            
            if chnl.id == CREATE_PRIVATE_ROOM: continue
            
            if not chnl.members: await chnl.delete()
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, 
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        
        if after.channel.id == CREATE_PRIVATE_ROOM: # Если чел зашёл в войс для создания приватки
                        
            session = get_async_session()
            
            private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == member.id))).scalar_one_or_none()
            
            if not private_room: return
            
            category:discord.CategoryChannel = await self.bot.fetch_channel(PRIVATE_CATEGORY)
            
            overwr_dict = {member: discord.PermissionOverwrite(connect=True,
                                                               #mute_members=True, # Под вопросом
                                                               #deafen_members=True, # Под вопросом
                                                               move_members=True,
                                                               speak=True, 
                                                               send_messages=True, 
                                                               stream=True,
                                                               read_messages=True, 
                                                               view_channel=True)}
            
            room_members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == private_room.id))).scalars().all()

            for room_mmbr in room_members:
                
                _ = await self.bot.fetch_user(room_mmbr.user_id)
                
                overwr_dict.update({_: discord.PermissionOverwrite(connect=True, 
                                                                   speak=True, 
                                                                   send_messages=True,
                                                                   stream=True,
                                                                   read_messages=True, 
                                                                   view_channel=True)})
            
            new_channel = await category.create_voice_channel(name=private_room.label,
                                                              overwrites=overwr_dict)
            
            await member.move_to(new_channel)
            
        elif before: # Если вышел из приватки
            
            if (before.channel.id != CREATE_PRIVATE_ROOM) and \
            (not before.channel.members) and (before.channel.category_id == PRIVATE_CATEGORY):
            
                await before.channel.delete()
            