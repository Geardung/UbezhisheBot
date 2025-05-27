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
        
        super().__init__()
    
    
    async def parse_time_counters(self):
        session = get_async_session()
        
        _ = TimeParse()
        session.add(_)
        await session.commit()
        await session.refresh(_)
        
        # Получаем все необработанные логи
        all_time_counters = (await session.execute(
            select(TimeCounterLog)
            .where(TimeCounterLog.parse_id == None)
            .order_by(TimeCounterLog.timestamp)
        )).scalars().all()
        
        # Группируем логи по пользователям
        user_logs = {}
        for log in all_time_counters:
            if log.user_id not in user_logs:
                user_logs[log.user_id] = []
            user_logs[log.user_id].append(log)
        
        # Обрабатываем логи для каждого пользователя
        for user_id, logs in user_logs.items():
            user = await session.get(User, user_id)
            if not user:
                user = User(id=user_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            # Сортируем логи по времени
            logs.sort(key=lambda x: x.timestamp)
            
            # Обрабатываем пары вход/выход
            i = 0
            while i < len(logs):
                current_log = logs[i]
                
                # Если это лог входа
                if current_log.log_type == VoiceLogTypeENUM.enter:
                    # Ищем следующий лог выхода для этого пользователя
                    next_exit = None
                    for j in range(i + 1, len(logs)):
                        if logs[j].user_id == user_id and logs[j].log_type == VoiceLogTypeENUM.exit:
                            next_exit = logs[j]
                            break
                    
                    if next_exit:
                        # Вычисляем время между входом и выходом
                        time_spent = next_exit.timestamp - current_log.timestamp
                        
                        # Если время проведено в голосовом канале
                        if time_spent > 0:
                            user.time_spended_summary += time_spent
                        
                        # Отмечаем логи как обработанные
                        current_log.parse_id = _.id
                        next_exit.parse_id = _.id
                        
                        # Пропускаем обработанные логи
                        i = j + 1
                        continue
                
                i += 1
            
            await session.commit()
        
        await session.close()
    
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
                                            user_name=ctx.interaction.user.display_name if not member else member.display_name, 
                                            time_spended_str=f"{days} дней {hours} часов {minutes} минут",
                                            member_img_url=ctx.interaction.user.display_avatar.url if not member else member.guild_avatar.url,
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
        
        session = get_async_session()
        
        if before.channel and ( not after.channel ): # Чел вышел из войса
            
            session.add(TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.exit,
                                            channel_id=before.channel.id))
            
        elif (not before.channel) and after.channel: # Чел Вошёл в войс
            
            if after.channel.id == 1314291685538271333: return # Проверка на AFK канал
            
            session.add(TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.enter,
                                            channel_id=after.channel.id))
            
        elif before.channel and after.channel: # Чел из одного в другой войс
            
            session.add_all([TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.exit,
                                            channel_id=before.channel.id),
                                 TimeCounterLog(user_id=member.id,
                                            log_type=VoiceLogTypeENUM.enter,
                                            channel_id=after.channel.id)])
        
        await session.commit()
        await session.close()