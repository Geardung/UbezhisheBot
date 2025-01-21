from datetime import datetime
import discord
from discord.ext import commands, tasks
from typing import Union
from database import get_async_session
from models import TimeCounterLog, TimeParse, User, VoiceLogTypeENUM
from utils import get_embeds
from sqlalchemy import select

class TimeCounterCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        
        self.bot: discord.Bot = bot
        
        self.parsing_loop.start()
        
        self.session = get_async_session()
        
        super().__init__()
    
    
    async def parse_time_counters(self):
                
        session = get_async_session()
        
        _ = TimeParse()
        
        session.add(_)
        await session.commit()
        await session.refresh(_)
        
        all_time_counters = (await session.execute(select(TimeCounterLog).where(TimeCounterLog.parse_id == None))).scalars().all()
        
        for time_counter in all_time_counters:
            user = await session.get(User, time_counter.user_id)
            
            print("working on ", time_counter.id, time_counter.log_type, time_counter.parse_id)
            
            if (int(datetime.now().timestamp()) - time_counter.timestamp) > 172800*2: # Я хз ваще чо делать в таком случае, но случай хуйня
                time_counter.parse_id = _.id 
                user.time_spended_summary += 3600
                
            elif time_counter.log_type == VoiceLogTypeENUM.enter:
                def find_first_exit_log() -> TimeCounterLog:
                    for log in all_time_counters:
                        if log.user_id == user.id and log.log_type == VoiceLogTypeENUM.exit and time_counter.id < log.id:
                            return log
                    return None

                exit_log = find_first_exit_log()
                if not exit_log: continue
                print("finded exit log ", exit_log.id)
                
                time_counter.parse_id = _.id
                exit_log.parse_id = _.id
                
                user.time_spended_summary += exit_log.timestamp - time_counter.timestamp
                
                print(time_counter.parse_id, exit_log.parse_id, user.time_spended_summary)
                
            await session.commit()
    
    @tasks.loop(minutes=10)
    async def parsing_loop(self): await self.parse_time_counters()
        
    
    time_group = discord.SlashCommandGroup("time")
    time_spend_subgroup = time_group.create_subgroup("spend")
    
    @time_spend_subgroup.command(name="count") # Команда для всех, чтобы можно было посмотреть текущее время
    async def time_spend_count_command(self, 
                                       ctx: discord.ApplicationContext,
                                       member: discord.Member = None):
        
        session = get_async_session()
        
        if not member: user = await session.get(User, ctx.interaction.user.id)
        else: user = await session.get(User, member.id)
        
        timeparse = (await session.execute(select(TimeParse))).scalars().all()
        timeparse = timeparse[-1] if timeparse else None
        
        days = user.time_spended_summary // 86400
        hours = (user.time_spended_summary % 86400) // 3600
        minutes = (user.time_spended_summary % 3600) // 60
        
        await ctx.respond(embeds=get_embeds("timecounter\spend",
                                            [datetime.fromtimestamp(float(timeparse.timestamp_start))],
                                            user_name=ctx.interaction.user.name, 
                                            time_spended_str=f"{days} дней {hours} часов {minutes} минут",
                                            member_img_url=ctx.interaction.user.display_avatar.url,
                          ))
        
        await session.close()
    
    @time_spend_subgroup.command(name="parse") # Команда для ручного запуска парсинга времени
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_parse_command(self, 
                                       ctx: discord.ApplicationContext ):
        
        await ctx.respond("Делаем парс...", ephemeral=True)
        
        await self.parse_time_counters()
        
        await ctx.followup.send("Успешно!", ephemeral=True)
    
    @time_spend_subgroup.command(name="set") # Вручную устанавливать время 
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_set_command(self,
                                     ctx: discord.ApplicationContext, 
                                     member: discord.Member, 
                                     count: int,
                                     session = get_async_session()):

        await ctx.respond(f"Устанавливаем для <@{member.id}> некоторое количество времени", 
                          ephemeral=True)
        
        user = await session.get(User, member.id)
        
        if not user: 
            user = User(id=member.id)
            session.add(user)
            await session.commit(user)
            await session.refresh(user)
            
        user.time_spended_summary += count
        
        await session.commit()
        await session.close()
        
    @time_spend_subgroup.command(name="add") # Вручную добавлять времечко
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_add_command(self, 
                                     ctx: discord.ApplicationContext, 
                                     member: discord.Member, 
                                     count: int,
                                     session = get_async_session()):
        
        await ctx.respond(f"Устанавливаем для <@{member.id}> некоторое количество времени", 
                          ephemeral=True)
        
        user = await session.get(User, member.id)
        
        if not user: 
            user = User(id=member.id)
            session.add(user)
            await session.commit(user)
            await session.refresh(user)
            
        user.time_spended_summary += count
        
        await session.commit()
        await session.close()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, 
                                    member:discord.Member, 
                                    before: Union[None, discord.VoiceState], 
                                    after: Union[None, discord.VoiceState]):
        
        if member.bot: return
        
        if before.channel and ( not after.channel ): # Чел вышел из войса
            
            self.session.add(TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.exit,
                                            channel_id=before.channel.id))
            
        elif (not before.channel) and after.channel: # Чел Вошёл в войс
            
            if after.channel.id == 1314291685538271333: return # Проверка на AFK канал
            
            self.session.add(TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.enter,
                                            channel_id=after.channel.id))
            
        elif before.channel and after.channel: # Чел из одного в другой войс
            
            self.session.add_all([TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.exit,
                                            channel_id=before.channel.id),
                                 TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.enter,
                                            channel_id=after.channel.id)])
        
        await self.session.commit()