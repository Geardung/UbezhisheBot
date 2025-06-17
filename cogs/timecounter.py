from datetime import datetime
import discord
from discord.ext import commands, tasks
from typing import Union
from utils.database import get_async_session
from utils.models import TimeCounterLog, TimeParse, User, VoiceLogTypeENUM
from utils.embeds import get_embeds
from sqlalchemy import select

class TimeCounterCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.parsing_loop.start()
        super().__init__()
    
    async def initialize_voice_users(self):
        """♂️DUNGEON MASTER♂️ Инициализация пользователей, находящихся в голосовых каналах при запуске бота"""
        async with get_async_session() as session:
            current_time = int(datetime.now().timestamp())
            
            # Проходим по всем серверам и голосовым каналам
            for guild in self.bot.guilds:
                for channel in guild.voice_channels:
                    # Пропускаем AFK канал
                    if channel.id == 1314291685538271333:
                        continue
                        
                    for member in channel.members:
                        if member.bot:
                            continue
                            
                        # Создаём лог входа для каждого пользователя, который уже в канале
                        session.add(TimeCounterLog(
                            user_id=member.id,
                            log_type=VoiceLogTypeENUM.enter,
                            channel_id=channel.id,
                            timestamp=current_time
                        ))
            
            await session.commit()

    async def create_artificial_exit_enter(self, user_id: int, channel_id: int, current_time: int):
        """♂️ Создаём искусственный выход-вход для пользователя, который сидит в канале"""
        async with get_async_session() as session:
            # Создаём лог выхода
            session.add(TimeCounterLog(
                user_id=user_id,
                log_type=VoiceLogTypeENUM.exit,
                channel_id=channel_id,
                timestamp=current_time
            ))
            
            # Создаём лог входа
            session.add(TimeCounterLog(
                user_id=user_id,
                log_type=VoiceLogTypeENUM.enter,
                channel_id=channel_id,
                timestamp=current_time
            ))
            
            await session.commit()

    async def parse_time_counters(self):
        """♂️DUNGEON MASTER♂️ Основная логика парсинга времени"""
        async with get_async_session() as session:
            
            # Создаём новую запись парсинга
            time_parse = TimeParse()
            session.add(time_parse)
            await session.commit()
            await session.refresh(time_parse)
            
            current_time = int(datetime.now().timestamp())
            
            # Сначала создаём искусственные выходы-входы для всех пользователей, которые сейчас в голосовых каналах
            for guild in self.bot.guilds:
                for channel in guild.voice_channels:
                    if channel.id == 1314291685538271333:  # Пропускаем AFK канал
                        continue
                        
                    for member in channel.members:
                        if member.bot:
                            continue
                            
                        await self.create_artificial_exit_enter(member.id, channel.id, current_time)
            
            # Получаем все необработанные логи
            unprocessed_logs = (await session.execute(
                select(TimeCounterLog)
                .where(TimeCounterLog.parse_id == None)
                .order_by(TimeCounterLog.timestamp)
            )).scalars().all()
            
            # Группируем логи по пользователям
            user_logs = {}
            for log in unprocessed_logs:
                if log.user_id not in user_logs:
                    user_logs[log.user_id] = []
                user_logs[log.user_id].append(log)
            
            # Обрабатываем логи для каждого пользователя
            for user_id, logs in user_logs.items():
                # Получаем или создаём пользователя
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
                            if (logs[j].user_id == user_id and 
                                logs[j].log_type == VoiceLogTypeENUM.exit and
                                logs[j].channel_id == current_log.channel_id):
                                next_exit = logs[j]
                                break
                        
                        if next_exit:
                            # Вычисляем время между входом и выходом
                            time_spent = next_exit.timestamp - current_log.timestamp
                            
                            # Если время проведено в голосовом канале (больше 0)
                            if time_spent > 0:
                                user.time_spended_summary += time_spent
                            
                            # Отмечаем логи как обработанные
                            current_log.parse_id = time_parse.id
                            next_exit.parse_id = time_parse.id
                            
                            # Пропускаем обработанные логи
                            i = j + 1
                            continue
                    
                    i += 1
                
                await session.commit()

    @tasks.loop(minutes=10)
    async def parsing_loop(self):
        """♂️ Запускаем парсинг каждые 10 минут"""
        await self.parse_time_counters()
    
    time_group = discord.SlashCommandGroup("time")
    time_spend_subgroup = time_group.create_subgroup("spend")
    
    @discord.command(name="online", description="Показать время, проведенное в голосовых каналах")
    async def time_spend_count_command(self, 
                                       ctx: discord.ApplicationContext,
                                       member: discord.Member = None):
        
        async with get_async_session() as session:
            
            if not member: 
                user = await session.get(User, ctx.interaction.user.id)
            else: 
                user = await session.get(User, member.id)
            
            # Получаем последний парсинг
            timeparse = (await session.execute(select(TimeParse))).scalars().all()
            timeparse = timeparse[-1] if timeparse else None
            
            # Вычисляем время в читаемом формате
            days = user.time_spended_summary // 86400
            hours = (user.time_spended_summary % 86400) // 3600
            minutes = (user.time_spended_summary % 3600) // 60
            
            await ctx.respond(embeds=get_embeds("timecounter/spend",
                                                [datetime.fromtimestamp(float(timeparse.timestamp_start))] if timeparse else [datetime.now()],
                                                user_name=ctx.interaction.user.display_name if not member else member.display_name, 
                                                time_spended_str=f"{days} дней {hours} часов {minutes} минут",
                                                member_img_url=(member.guild_avatar.url if member.guild_avatar else "https://www.kino-teatr.ru/acter/album/7517/804691.jpg") if member else ctx.interaction.user.display_avatar.url,
                              ))
    
    @time_spend_subgroup.command(name="parse") # Команда для ручного запуска парсинга времени
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_parse_command(self, 
                                       ctx: discord.ApplicationContext ):
        
        await ctx.respond("♂️DUNGEON MASTER♂️ Делаем парс...", ephemeral=True)
        
        await self.parse_time_counters()
        
        await ctx.followup.send("♂️ Успешно! ♂️", ephemeral=True)
    
    @time_spend_subgroup.command(name="set") # Вручную устанавливать время 
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_set_command(self,
                                     ctx: discord.ApplicationContext, 
                                     member: discord.Member, 
                                     count: int):

        async with get_async_session() as session:
            await ctx.respond(f"♂️ Устанавливаем для <@{member.id}> некоторое количество времени", 
                              ephemeral=True)
            
            user = await session.get(User, member.id)
            
            if not user: 
                user = User(id=member.id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
            user.time_spended_summary = count
            
            await session.commit()
        
    @time_spend_subgroup.command(name="add") # Вручную добавлять времечко
    @commands.has_guild_permissions(administrator=True)
    async def time_spend_add_command(self, 
                                     ctx: discord.ApplicationContext, 
                                     member: discord.Member, 
                                     count: int):
        
        async with get_async_session() as session:
            await ctx.respond(f"♂️ Добавляем для <@{member.id}> некоторое количество времени", 
                              ephemeral=True)
            
            user = await session.get(User, member.id)
            
            if not user: 
                user = User(id=member.id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
            user.time_spended_summary += count
            
            await session.commit()
    
    @time_spend_subgroup.command(name="top", description="Показать топ игроков по времени в голосовых каналах")
    async def time_spend_top_command(self,
                                    ctx: discord.ApplicationContext,
                                    period: str = discord.Option(description="Период времени", choices=["3 дня", "7 дней", "30 дней"], default="7 дней")):
        
        async with get_async_session() as session:
            
            # Определяем timestamp для начала периода
            current_time = int(datetime.now().timestamp())
            if period == "3 дня":
                start_time = current_time - (3 * 24 * 3600)
            elif period == "7 дней":
                start_time = current_time - (7 * 24 * 3600)
            else:  # 30 дней
                start_time = current_time - (30 * 24 * 3600)
            
            # Получаем все логи за период
            logs = (await session.execute(
                select(TimeCounterLog)
                .where(TimeCounterLog.timestamp >= start_time)
                .order_by(TimeCounterLog.timestamp)
            )).scalars().all()
            
            # Группируем логи по пользователям
            user_times = {}
            for log in logs:
                if log.user_id not in user_times:
                    user_times[log.user_id] = []
                user_times[log.user_id].append(log)
            
            # Вычисляем время для каждого пользователя
            user_total_times = {}
            for user_id, user_logs in user_times.items():
                total_time = 0
                i = 0
                while i < len(user_logs):
                    current_log = user_logs[i]
                    
                    if current_log.log_type == VoiceLogTypeENUM.enter:
                        next_exit = None
                        for j in range(i + 1, len(user_logs)):
                            if (user_logs[j].user_id == user_id and 
                                user_logs[j].log_type == VoiceLogTypeENUM.exit and
                                user_logs[j].channel_id == current_log.channel_id):
                                next_exit = user_logs[j]
                                break
                        
                        if next_exit:
                            time_spent = next_exit.timestamp - current_log.timestamp
                            if time_spent > 0:
                                total_time += time_spent
                            i = j + 1
                            continue
                    i += 1
                
                user_total_times[user_id] = total_time
            
            # Сортируем пользователей по времени
            sorted_users = sorted(user_total_times.items(), key=lambda x: x[1], reverse=True)
            
            # Формируем топ-10
            top_users = []
            for user_id, time in sorted_users[:10]:
                member: discord.Member = ctx.guild.get_member(user_id)
                if member:
                    days = time // 86400
                    hours = (time % 86400) // 3600
                    minutes = (time % 3600) // 60
                    time_str = f"{days}д {hours}ч {minutes}м"
                    top_users.append((member.mention, time_str))
            
            # Создаём эмбед
            embed = discord.Embed(
                title=f"♂️ Топ-10 по онлайну за {period} ♂️",
                color=discord.Color.blue()
            )
            
            for i, (name, time) in enumerate(top_users, 1):
                embed.add_field(
                    name=f"#{i} {name}",
                    value=time,
                    inline=False
                )
            
            await ctx.respond(embed=embed)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, 
                                    member: discord.Member, 
                                    before: Union[None, discord.VoiceState], 
                                    after: Union[None, discord.VoiceState]):
        
        if member.bot: 
            return
        
        async with get_async_session() as session:
            
            if before.channel and not after.channel:  # Чел вышел из войса
                session.add(TimeCounterLog(
                    user_id=member.id,
                    log_type=VoiceLogTypeENUM.exit,
                    channel_id=before.channel.id
                ))
                
            elif not before.channel and after.channel:  # Чел вошёл в войс
                if after.channel.id == 1314291685538271333:  # Проверка на AFK канал
                    return
                
                session.add(TimeCounterLog(
                    user_id=member.id,
                    log_type=VoiceLogTypeENUM.enter,
                    channel_id=after.channel.id
                ))
                
            elif before.channel and after.channel:  # Чел из одного в другой войс
                # Сначала выход из старого канала
                session.add(TimeCounterLog(
                    user_id=member.id,
                    log_type=VoiceLogTypeENUM.exit,
                    channel_id=before.channel.id
                ))
                
                # Затем вход в новый канал
                if after.channel.id != 1314291685538271333:  # Проверка на AFK канал
                    session.add(TimeCounterLog(
                        user_id=member.id,
                        log_type=VoiceLogTypeENUM.enter,
                        channel_id=after.channel.id
                    ))
            
            await session.commit()


def setup(bot): # this is called by Pycord to setup the cog
    bot.add_cog(TimeCounterCog(bot)) # add the cog to the bot