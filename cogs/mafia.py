from datetime import datetime, timedelta
import discord
from discord.ext import commands, tasks
from typing import Union, Optional
from database import get_async_session
from models import (
    MafiaGame, MafiaPlayer, MafiaRole, MafiaGameLog, MafiaRoleSetting,
    MafiaGameStatusENUM, MafiaTeamENUM, MafiaActionTypeENUM, User
)
from utils import get_embeds
from sqlalchemy import select, and_, or_
import random
import asyncio

class JoinButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤПрисоединитьсяㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ", style=discord.ButtonStyle.green)
    async def join_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == interaction.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.LOBBY.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.followup.send("Сейчас нет активной игры в лобби!", ephemeral=True)
                return
            
            # Проверяем, не в игре ли уже игрок
            existing_player = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.user_id == interaction.user.id
                    )
                )
            )
            if existing_player.scalar_one_or_none():
                await interaction.followup.send("Вы уже в игре!", ephemeral=True)
                return
            
            # Добавляем игрока
            player = MafiaPlayer(
                game_id=game.id,
                user_id=interaction.user.id
            )
            session.add(player)
            await session.commit()
        
        # Уведомляем об этом в основном чате
        main_channel = interaction.client.get_channel(game.main_text_channel_id)
        if main_channel:
            embeds = get_embeds("mafia/player_joined",
                playerName=interaction.user.display_name
            )
            await main_channel.send(embeds=embeds)
            
            # Обновляем эмбед лобби
            await self.cog.update_lobby_embed(game.id)
        
        await interaction.followup.send("Вы присоединились к игре!", ephemeral=True)

class MafiaCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        self.active_games = {}  # game_id: game_data
        super().__init__()
        
        # Регистрируем обработчик для Select меню
        self.bot.add_listener(self.on_select_vote, "on_select_option")
    
    mafia_group = discord.SlashCommandGroup("mafia")
    leader_group = mafia_group.create_subgroup("leader", "Команды для ведущего игры")
    
    async def update_lobby_embed(self, game_id: int):
        """Обновляет эмбед лобби с информацией об игроках"""
        async with get_async_session() as session:
            # Получаем игру
            game = await session.execute(
                select(MafiaGame).where(MafiaGame.id == game_id)
            )
            game = game.scalar_one_or_none()
            
            if not game or not game.lobby_message_id:
                return
            
            # Получаем список игроков
            players = await session.execute(
                select(MafiaPlayer).where(MafiaPlayer.game_id == game.id)
            )
            players = players.scalars().all()
            
            # Получаем статистику игроков
            player_stats = {}
            for player in players:
                # Получаем количество побед и поражений
                wins = await session.execute(
                    select(MafiaGame).where(
                        and_(
                            MafiaGame.guild_id == game.guild_id,
                            MafiaGame.status == MafiaGameStatusENUM.FINISHED.value,
                            MafiaGame.winner_team == MafiaTeamENUM.TOWN.value,
                            MafiaPlayer.game_id == MafiaGame.id,
                            MafiaPlayer.user_id == player.user_id,
                            MafiaPlayer.is_alive == True
                        )
                    )
                )
                losses = await session.execute(
                    select(MafiaGame).where(
                        and_(
                            MafiaGame.guild_id == game.guild_id,
                            MafiaGame.status == MafiaGameStatusENUM.FINISHED.value,
                            MafiaPlayer.game_id == MafiaGame.id,
                            MafiaPlayer.user_id == player.user_id,
                            MafiaPlayer.is_alive == False
                        )
                    )
                )
                player_stats[player.user_id] = {
                    "wins": len(wins.scalars().all()),
                    "losses": len(losses.scalars().all())
                }
            
            # Формируем список игроков с их статистикой
            players_list = []
            for player in players:
                user = self.bot.get_user(player.user_id)
                if user:
                    stats = player_stats[player.user_id]
                    players_list.append(f"👤 {user.display_name} (Побед: {stats['wins']}, Поражений: {stats['losses']})")
            
            # Получаем сообщение с эмбедом
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                try:
                    message = await main_channel.fetch_message(game.lobby_message_id)
                    if message:
                        # Обновляем эмбед
                        embeds = get_embeds("mafia/game_created",
                            creatorName=self.bot.get_user(game.leader_id).display_name,
                            joinCommand="`/mafia join`",
                            playersList="\n".join(players_list) if players_list else "Пока нет игроков"
                        )
                        await message.edit(embeds=embeds)
                except:
                    pass
    
    @mafia_group.command(name="create")
    async def mafia_create_command(self, ctx: discord.ApplicationContext):
        """Создать новую игру в мафию"""
        await ctx.defer(ephemeral=True)
        
        # Проверяем, нет ли уже активной игры
        async with get_async_session() as session:
            active_game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status.in_([MafiaGameStatusENUM.LOBBY.value, MafiaGameStatusENUM.RUNNING.value])
                    )
                )
            )
            if active_game.scalar_one_or_none():
                await ctx.followup.send("В этом сервере уже есть активная игра!", ephemeral=True)
                return
        
        # Создаем категорию для игры
        category = await ctx.guild.create_category("🎭 Мафия", position=0)
        
        # Создаем каналы
        main_text = await category.create_text_channel("общий-чат")
        log_text = await category.create_text_channel("лог-игры")
        main_voice = await category.create_voice_channel("🔊 Собрание")
        mafia_voice = await category.create_voice_channel("🕵️ Дом Мафии")
        cemetery_voice = await category.create_voice_channel("👻 Кладбище")
        
        # Создаем игру в базе данных
        async with get_async_session() as session:
            game = MafiaGame(
                guild_id=ctx.guild_id,
                category_channel_id=category.id,
                main_voice_channel_id=main_voice.id,
                main_text_channel_id=main_text.id,
                mafia_voice_channel_id=mafia_voice.id,
                cemetery_voice_channel_id=cemetery_voice.id,
                log_text_channel_id=log_text.id,
                leader_id=ctx.author.id,
                status=MafiaGameStatusENUM.LOBBY.value
            )
            session.add(game)
            await session.commit()
            
            # Добавляем создателя в игру
            player = MafiaPlayer(
                game_id=game.id,
                user_id=ctx.author.id
            )
            session.add(player)
            await session.commit()
        
        # Отправляем приветственное сообщение с кнопкой
        embeds = get_embeds("mafia/game_created", 
            creatorName=ctx.author.display_name,
            joinCommand="`/mafia join`",
            playersList="Пока нет игроков"
        )
        view = JoinButton()
        message = await main_text.send(embeds=embeds, view=view)
        
        # Сохраняем ID сообщения
        game.lobby_message_id = message.id
        await session.commit()
        
        # Создаем событие
        event = await ctx.guild.create_scheduled_event(
            name="🎭 Игра в Мафию",
            description="Присоединяйтесь к игре в Мафию!",
            start_time=datetime.now() + timedelta(minutes=5),
            end_time=datetime.now() + timedelta(hours=2),
            channel=main_voice
        )
        
        # Входим в войс канал
        await main_voice.connect()
        
        # Меняем никнейм бота
        await ctx.guild.me.edit(nick="DJ колонка")
        
        await ctx.followup.send("Игра создана! Присоединяйтесь через кнопку или команду `/mafia join`", ephemeral=True)
    
    @mafia_group.command(name="join")
    async def mafia_join_command(self, ctx: discord.ApplicationContext):
        """Присоединиться к игре в мафию"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.LOBBY.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("Сейчас нет активной игры в лобби!", ephemeral=True)
                return
            
            # Проверяем, не в игре ли уже игрок
            existing_player = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.user_id == ctx.author.id
                    )
                )
            )
            if existing_player.scalar_one_or_none():
                await ctx.followup.send("Вы уже в игре!", ephemeral=True)
                return
            
            # Добавляем игрока
            player = MafiaPlayer(
                game_id=game.id,
                user_id=ctx.author.id
            )
            session.add(player)
            await session.commit()
        
        # Уведомляем об этом в основном чате
        main_channel = self.bot.get_channel(game.main_text_channel_id)
        if main_channel:
            embeds = get_embeds("mafia/player_joined",
                playerName=ctx.author.display_name
            )
            await main_channel.send(embeds=embeds)
        
        await ctx.followup.send("Вы присоединились к игре!", ephemeral=True)
    
    @mafia_group.command(name="start")
    async def mafia_start_command(self, ctx: discord.ApplicationContext):
        """Начать игру в мафию"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.LOBBY.value,
                        MafiaGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для начала игры или игра не найдена!", ephemeral=True)
                return
            
            # Получаем список игроков
            players = await session.execute(
                select(MafiaPlayer).where(MafiaPlayer.game_id == game.id)
            )
            players = players.scalars().all()
            
            # Убираем ведущего из списка игроков
            players = [p for p in players if p.user_id != game.leader_id]
            
            if len(players) < 4:
                await ctx.followup.send("Для начала игры нужно минимум 4 игрока!", ephemeral=True)
                return
            
            # Получаем базовые роли
            roles = await session.execute(
                select(MafiaRole).where(MafiaRole.is_custom_role == False)
            )
            roles = roles.scalars().all()
            
            if not roles:
                await ctx.followup.send("Ошибка: базовые роли не найдены в базе данных!", ephemeral=True)
                return
            
            # Распределяем роли
            random.shuffle(players)
            role_index = 0
            
            for player in players:
                player.role_id = roles[role_index].id
                role_index = (role_index + 1) % len(roles)
            
            # Обновляем статус игры
            game.status = MafiaGameStatusENUM.RUNNING.value
            game.start_time = int(datetime.now().timestamp())
            await session.commit()
            
            # Отправляем роли игрокам
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                embeds = get_embeds("mafia/game_started")
                await main_channel.send(embeds=embeds)
            
            for player in players:
                user = self.bot.get_user(player.user_id)
                if user:
                    role = next(r for r in roles if r.id == player.role_id)
                    embeds = get_embeds("mafia/role_assignment",
                        playerName=user.display_name,
                        roleName=role.role_name,
                        teamName=role.team.value,
                        roleDescription=role.role_description,
                        roleAbilities=str(role.abilities),
                        roleColor="#" + hex(random.randint(0, 0xFFFFFF))[2:].zfill(6),
                        roleIconUrl=user.display_avatar.url
                    )
                    await user.send(embeds=embeds)
            
            await ctx.followup.send("Игра началась! Роли разосланы игрокам.", ephemeral=True)
            
            # Запускаем первый день
            await self.start_day(game.id)
    
    async def start_day(self, game_id: int):
        """Начать дневную фазу"""
        async with get_async_session() as session:
            game = await session.execute(
                select(MafiaGame).where(MafiaGame.id == game_id)
            )
            game = game.scalar_one_or_none()
            
            if not game:
                return
            
            # Логируем начало дня
            log = MafiaGameLog(
                game_id=game.id,
                phase="day",
                action_type=MafiaActionTypeENUM.GAME_START
            )
            session.add(log)
            await session.commit()
            
            # Отправляем сообщение о начале дня
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                embeds = get_embeds("mafia/day_starts",
                    nightResults="Город просыпается...",
                    dayImageUrl="https://example.com/day.jpg"  # TODO: Добавить реальные изображения
                )
                await main_channel.send(embeds=embeds)
    
    @mafia_group.command(name="vote")
    async def mafia_vote_command(self, 
                               ctx: discord.ApplicationContext,
                               target: discord.Member):
        """Голосовать за исключение игрока"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем, идет ли игра
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("Сейчас нет активной игры!", ephemeral=True)
                return
            
            # Проверяем, жив ли голосующий
            voter = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.user_id == ctx.author.id,
                        MafiaPlayer.is_alive == True
                    )
                )
            )
            voter = voter.scalar_one_or_none()
            
            if not voter:
                await ctx.followup.send("Вы не можете голосовать!", ephemeral=True)
                return
            
            # Проверяем, жив ли цель
            target_player = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.user_id == target.id,
                        MafiaPlayer.is_alive == True
                    )
                )
            )
            target_player = target_player.scalar_one_or_none()
            
            if not target_player:
                await ctx.followup.send("Нельзя голосовать за мертвого игрока!", ephemeral=True)
                return
            
            # Логируем голос
            log = MafiaGameLog(
                game_id=game.id,
                actor_player_id=voter.id,
                target_player_id=target_player.id,
                action_type=MafiaActionTypeENUM.VOTE
            )
            session.add(log)
            await session.commit()
            
            await ctx.followup.send(f"Ваш голос за {target.display_name} учтен!", ephemeral=True)
    
    @mafia_group.command(name="end")
    async def mafia_end_command(self, ctx: discord.ApplicationContext):
        """Завершить игру в мафию"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права и статус игры
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.leader_id == ctx.author.id,
                        MafiaGame.status.in_([
                            MafiaGameStatusENUM.RUNNING.value,
                            MafiaGameStatusENUM.LOBBY.value
                        ])
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для завершения игры или игра не найдена!", ephemeral=True)
                return
            
            # Обновляем статус игры
            game.status = MafiaGameStatusENUM.FINISHED.value
            game.end_time = int(datetime.now().timestamp())
            await session.commit()
            
            # Отправляем сообщение о завершении
            await ctx.followup.send("Игра завершена!", ephemeral=True)
            
            # Перемещаем и переименовываем канал логов
            logs_channel = self.bot.get_channel(game.log_text_channel_id)
            if logs_channel:
                category = self.bot.get_channel(1377049915993096243)
                if category:
                    await logs_channel.edit(
                        category=category,
                        name=f"Мафия-{game.id}-{datetime.now().strftime('%Y%m%d')}"
                    )
            
            # Удаляем все игровые каналы кроме логов
            if game.main_text_channel_id:
                main_channel = self.bot.get_channel(game.main_text_channel_id)
                if main_channel:
                    await main_channel.delete()
            
            if game.main_voice_channel_id:
                voice_channel = self.bot.get_channel(game.main_voice_channel_id)
                if voice_channel:
                    await voice_channel.delete()
            
            if game.mafia_voice_channel_id:
                mafia_voice = self.bot.get_channel(game.mafia_voice_channel_id)
                if mafia_voice:
                    await mafia_voice.delete()
            
            if game.cemetery_voice_channel_id:
                cemetery_voice = self.bot.get_channel(game.cemetery_voice_channel_id)
                if cemetery_voice:
                    await cemetery_voice.delete()
            
            if game.category_channel_id:
                category = self.bot.get_channel(game.category_channel_id)
                if category:
                    await category.delete()
            
            # Отправляем сообщение о завершении в лог
            if logs_channel:
                embeds = get_embeds("mafia/game_result",
                    winnerTeam="Игра принудительно завершена",
                    winnerColor="#95A5A6",
                    winnerList="Игра была остановлена ведущим",
                    gameStats="Статистика недоступна",
                    resultImageUrl="https://example.com/end.jpg"  # TODO: Добавить реальные изображения
                )
                await logs_channel.send(embeds=embeds)
    
    @leader_group.command(name="voting")
    async def leader_voting_command(self, ctx: discord.ApplicationContext):
        """Начать этап голосования"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.RUNNING.value,
                        MafiaGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            # Получаем список живых игроков
            players = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.is_alive == True
                    )
                )
            )
            players = players.scalars().all()
            
            if len(players) < 2:
                await ctx.followup.send("Для голосования нужно минимум 2 живых игрока!", ephemeral=True)
                return
            
            # Создаем Select меню для каждого игрока
            for player in players:
                user = self.bot.get_user(player.user_id)
                if user:
                    # Создаем список опций для Select
                    options = []
                    for target in players:
                        if target.id != player.id:  # Нельзя голосовать за себя
                            target_user = self.bot.get_user(target.user_id)
                            if target_user:
                                options.append(
                                    discord.SelectOption(
                                        label=target_user.display_name,
                                        value=str(target.id),
                                        description=f"Проголосовать за {target_user.display_name}"
                                    )
                                )
                    
                    # Создаем Select меню
                    select = discord.ui.Select(
                        placeholder="Выберите игрока для голосования",
                        options=options,
                        custom_id=f"vote_{game.id}_{player.id}_{game.current_round}"  # Добавляем номер раунда
                    )
                    
                    # Создаем View с Select
                    view = discord.ui.View()
                    view.add_item(select)
                    
                    # Отправляем сообщение с Select
                    embeds = get_embeds("mafia/voting_starts",
                        votingTime="60",  # TODO: Сделать настраиваемым
                        roundNumber=game.current_round
                    )
                    await user.send(embeds=embeds, view=view)
            
            # Отправляем сообщение в основной чат
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                embeds = get_embeds("mafia/voting_starts",
                    votingTime="60",  # TODO: Сделать настраиваемым
                    roundNumber=game.current_round
                )
                await main_channel.send(embeds=embeds)
            
            await ctx.followup.send("Голосование начато! Игроки получили личные сообщения с выбором.", ephemeral=True)
    
    @leader_group.command(name="stopvoting")
    async def leader_stopvoting_command(self, ctx: discord.ApplicationContext):
        """Завершить этап голосования"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.RUNNING.value,
                        MafiaGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            # Получаем все голоса за текущий раунд
            votes = await session.execute(
                select(MafiaGameLog).where(
                    and_(
                        MafiaGameLog.game_id == game.id,
                        MafiaGameLog.action_type == MafiaActionTypeENUM.VOTE,
                        MafiaGameLog.round_number == game.current_round
                    )
                ).order_by(MafiaGameLog.timestamp.desc())
            )
            votes = votes.scalars().all()
            
            # Подсчитываем голоса
            vote_count = {}
            for vote in votes:
                if vote.target_player_id not in vote_count:
                    vote_count[vote.target_player_id] = 0
                vote_count[vote.target_player_id] += 1
            
            if not vote_count:
                await ctx.followup.send("Никто не проголосовал!", ephemeral=True)
                return
            
            # Находим игрока с максимальным количеством голосов
            max_votes = max(vote_count.values())
            eliminated_players = [pid for pid, votes in vote_count.items() if votes == max_votes]
            
            if len(eliminated_players) > 1:
                await ctx.followup.send("Ничья в голосовании! Нужно переголосование.", ephemeral=True)
                return
            
            eliminated_id = eliminated_players[0]
            
            # Получаем информацию об исключенном игроке
            eliminated = await session.execute(
                select(MafiaPlayer).where(
                    and_(
                        MafiaPlayer.game_id == game.id,
                        MafiaPlayer.id == eliminated_id
                    )
                )
            )
            eliminated = eliminated.scalar_one_or_none()
            
            if not eliminated:
                await ctx.followup.send("Ошибка: игрок не найден!", ephemeral=True)
                return
            
            # Получаем роль исключенного игрока
            role = await session.execute(
                select(MafiaRole).where(MafiaRole.id == eliminated.role_id)
            )
            role = role.scalar_one_or_none()
            
            # Обновляем статус игрока
            eliminated.is_alive = False
            eliminated.death_reason = "Повешен по решению города"
            eliminated.death_night_number = game.current_round
            await session.commit()
            
            # Отправляем сообщение об исключении
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                eliminated_user = self.bot.get_user(eliminated.user_id)
                if eliminated_user and role:
                    embeds = get_embeds("mafia/player_eliminated",
                        playerName=eliminated_user.display_name,
                        playerRole=role.role_name,
                        playerTeam=role.team.value,
                        deathReason="Повешен по решению города",
                        playerAvatarUrl=eliminated_user.display_avatar.url
                    )
                    await main_channel.send(embeds=embeds)
            
            await ctx.followup.send("Голосование завершено! Результаты объявлены в основном чате.", ephemeral=True)
    
    @leader_group.command(name="night")
    async def leader_night_command(self, ctx: discord.ApplicationContext):
        """Начать ночную фазу"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.RUNNING.value,
                        MafiaGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            # Логируем начало ночи
            log = MafiaGameLog(
                game_id=game.id,
                phase="night",
                action_type=MafiaActionTypeENUM.GAME_START
            )
            session.add(log)
            await session.commit()
            
            # Отправляем сообщение о начале ночи
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                embeds = get_embeds("mafia/night_starts",
                    nightImageUrl="https://example.com/night.jpg"  # TODO: Добавить реальные изображения
                )
                await main_channel.send(embeds=embeds)
            
            # TODO: Реализовать ночные действия ролей
            
            await ctx.followup.send("Ночь наступила! Роли могут выполнять свои действия.", ephemeral=True)
    
    @leader_group.command(name="day")
    async def leader_day_command(self, ctx: discord.ApplicationContext):
        """Начать дневную фазу"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.guild_id == ctx.guild_id,
                        MafiaGame.status == MafiaGameStatusENUM.RUNNING.value,
                        MafiaGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            # Логируем начало дня
            log = MafiaGameLog(
                game_id=game.id,
                phase="day",
                action_type=MafiaActionTypeENUM.GAME_START
            )
            session.add(log)
            await session.commit()
            
            # Отправляем сообщение о начале дня
            main_channel = self.bot.get_channel(game.main_text_channel_id)
            if main_channel:
                embeds = get_embeds("mafia/day_starts",
                    nightResults="Город просыпается...",
                    dayImageUrl="https://example.com/day.jpg"  # TODO: Добавить реальные изображения
                )
                await main_channel.send(embeds=embeds)
            
            await ctx.followup.send("День наступил! Город просыпается.", ephemeral=True)
        
    async def on_select_vote(self, interaction: discord.Interaction):
        """Обработчик выбора в Select меню голосования"""
        if not interaction.data.get("custom_id", "").startswith("vote_"):
            return
        
        # Получаем данные из custom_id
        _, game_id, voter_id, round_number = interaction.data["custom_id"].split("_")
        game_id = int(game_id)
        voter_id = int(voter_id)
        round_number = int(round_number)
        
        # Проверяем, что голосующий - это тот, кто нажал
        if interaction.user.id != voter_id:
            await interaction.response.send_message("Это не ваше меню голосования!", ephemeral=True)
            return
        
        # Получаем выбранного игрока
        selected_id = int(interaction.data["values"][0])
        
        async with get_async_session() as session:
            # Проверяем, что раунд все еще актуален
            game = await session.execute(
                select(MafiaGame).where(
                    and_(
                        MafiaGame.id == game_id,
                        MafiaGame.current_round == round_number
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.response.send_message("Это голосование уже завершено!", ephemeral=True)
                return
            
            # Логируем голос
            log = MafiaGameLog(
                game_id=game_id,
                actor_player_id=voter_id,
                target_player_id=selected_id,
                action_type=MafiaActionTypeENUM.VOTE,
                round_number=round_number
            )
            session.add(log)
            await session.commit()
        
        # Отправляем подтверждение
        await interaction.response.send_message("Ваш голос учтен!", ephemeral=True)
        