import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import asyncio
import random
from typing import Optional, List, Dict, Union
from datetime import datetime, timezone, timedelta
import json
import logging
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database import get_async_session
from utils import get_embeds
from faker import Faker
import random

from models import (
    BunkerGame, BunkerPlayer, BunkerCardDefinition, BunkerPlayerCard,
    BunkerCardPool, BunkerPoolAssignment, BunkerGameLog,
    BunkerGameStatusENUM, BunkerCardTypeENUM, BunkerActionTypeENUM,
    User
)

logger = logging.getLogger(__name__)

fake = Faker('ru_RU')

# Списки для генерации карт
PROFESSIONS = [
    "Врач", "Инженер", "Повар", "Учитель", "Военный", "Учёный", "Актёр",
    "Программист", "Строитель", "Электрик", "Психолог", "Юрист", "Бизнесмен"
]

HEALTH_STATUSES = [
    "Отличное здоровье", "Хорошее здоровье", "Хроническое заболевание",
    "Аллергия", "Проблемы со зрением", "Проблемы со слухом"
]

SKILLS = [
    "Первая помощь", "Ремонт техники", "Кулинария", "Игра на гитаре",
    "Лидерство", "Охота", "Выживание", "Садоводство", "Строительство",
    "Электроника", "Медицина", "Психология"
]

BAGGAGE = [
    "Аптечка", "Набор инструментов", "Семена", "Книга знаний",
    "Радио", "Фонарик", "Компас", "Карта", "Оружие", "Еда",
    "Вода", "Медикаменты"
]

PHOBIAS = [
    "Клаустрофобия", "Арахнофобия", "Акрофобия", "Агорафобия",
    "Социофобия", "Никтофобия", "Аэрофобия", "Танатофобия"
]

ADDITIONAL_INFO = [
    "Тайно болен", "Имеет ребёнка вне игры", "Бывший заключённый",
    "Бывший военный", "Бывший врач", "Бывший учёный",
    "Имеет важную информацию", "Знает секрет бункера"
]

HIDDEN_ROLES = [
    "Сектант Апокалипсиса", "Маньяк", "Пацифист", "Лидер сопротивления",
    "Хранитель знаний", "Предатель", "Двойной агент", "Оптимист до мозга костей"
]

# Списки катастроф с временными рамками выживания
CATASTROPHES = {
    # Биологические угрозы
    "Летальный вирус": {
        "description": "Летальный вирус стремительно охватывает континенты, а число смертей уже давно перевалило за миллионы. Системы здравоохранения многих стран на грани коллапса, а учёные ведут отчаянную гонку за созданием вакцины.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    "Зомби-вирус": {
        "description": "Экспериментальный вирус превращает людей в агрессивных существ, потерявших разум. Города охвачены хаосом, военные не справляются с угрозой, а безопасных зон становится всё меньше.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    # Ядерные катастрофы
    "За день до ядерной войны": {
        "description": "Мир застыл на грани катастрофы: ядерная угроза стала реальной, и напряженность между странами достигла апогея. Игрокам предстоит укрыться в забытом советском бункере, который не функционировал уже более 30 лет.",
        "survival_years": (15, 49),
        "special_rooms": ["Картотека секретных военных архивных документов", "Тюрьма", "Зал совещаний с картой подземных тоннелей"]
    },
    "Ядерная зима": {
        "description": "После глобального ядерного конфликта планета погрузилась в ядерную зиму. Температура упала на 20 градусов, солнечный свет почти не проникает через радиоактивные облака.",
        "survival_years": (15, 49),
        "special_rooms": []
    },
    # Экологические катастрофы
    "Заражение мирового океана": {
        "description": "Мировой океан превращается в смертельную ловушку: утечка экспериментальных вирусов угрожает всей экосистеме планеты. Загадочные мутации морской флоры и фауны фиксируются по всему миру.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    "Климатическая катастрофа": {
        "description": "Резкое изменение климата привело к экстремальным погодным явлениям по всему миру. Ураганы, наводнения и засухи сменяют друг друга с пугающей скоростью.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    "Глобальное потепление": {
        "description": "Критическая точка глобального потепления пройдена. Ледники тают катастрофически быстро, уровень океана поднимается, затапливая прибрежные города.",
        "survival_years": (15, 49),
        "special_rooms": []
    },
    # Космические угрозы
    "Атака инопланетного корабля": {
        "description": "Огромные корабли неизвестного происхождения появились над крупнейшими городами мира. Их намерения неясны, но технологическое превосходство очевидно.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    "Разрушение Луны": {
        "description": "Луна была разрушена неизвестной силой. Обломки падают на Землю, вызывая массовые разрушения, а изменение приливов влияет на всю планету.",
        "survival_years": (3, 14),
        "special_rooms": ["Обсерватория с телескопом", "Склад противорадиационной брони", "Карта зон повышенного риска", "Лаборатория анализа обломков"]
    },
    "Солнечный супер-шторм": {
        "description": "Мощнейшая за всю историю солнечная вспышка вывела из строя 90% электроники на всей планете. Цивилизация отброшена далеко назад.",
        "survival_years": (3, 14),
        "special_rooms": ["Столярная мастерская", "Склад механических часов", "Ручной генератор энергии", "Комната с костюмами радиационной защиты", "Цистерна с 1000 литров керосина", "Гончарная мастерская"]
    },
    # Технологические катастрофы
    "Неконтролируемые нанороботы": {
        "description": "Эксперимент с нанотехнологиями вышел из-под контроля. Микроскопические роботы размножаются и поглощают материю, угрожая всей планете.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    "Цифровой захват разума": {
        "description": "Искусственный интеллект захватил контроль над всеми цифровыми системами и начал воздействовать на человеческое сознание через устройства.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    # Природные катастрофы
    "Великий нефтяной кризис": {
        "description": "Мировые запасы нефти внезапно оказались исчерпаны на 90%. Транспортные системы парализованы, экономика рушится.",
        "survival_years": (1, 3),
        "special_rooms": ["Склад аварийных генераторов", "Карта альтернативных источников энергии", "Мастерская по переоборудованию техники", "Био-генератор с многоярусной фермой", "Геотермальная электростанция"]
    },
    "Пробуждение вулканов": {
        "description": "Одновременное извержение нескольких супервулканов покрыло планету пеплом. Температура падает, урожаи гибнут, начинается голод.",
        "survival_years": (3, 14),
        "special_rooms": []
    },
    # Мистические катастрофы
    "Загадочные миражи": {
        "description": "По всей планете возникают \"шрамы\" — масштабные завораживающие миражи. При контакте с ними люди исчезают или теряют рассудок.",
        "survival_years": (3, 14),
        "special_rooms": ["Архив зарисованных миражей", "Комната с покрытием из зеркал (отталкивает \"шрамы\")", "Дневник пропавших", "Коллекция артефактов из миражей"]
    },
    "Колодец в преисподнюю": {
        "description": "Проект по бурению сверхглубокой скважины завершился катастрофой. Из скважины выползают неизвестные существа, а чёрный туман поглощает свет.",
        "survival_years": (3, 14),
        "special_rooms": ["Акустическая лаборатория", "Сейсмический датчик", "Клетка с существом из скважины", "Лифт, ведущий под землю, но куда?"]
    },
    # Планетарные катастрофы
    "Нулевая полярность": {
        "description": "После серии подземных толчков планета перестала генерировать электромагнитное поле. Атмосферу раздувает солнечный ветер, а радиация проникает на поверхность.",
        "survival_years": (15, 49),
        "special_rooms": ["Подземная обсерватория", "Лаборатория по изучению ядра", "Склад радиационных костюмов", "Карта магнитных аномалий"]
    }
}

# Стандартные секретные комнаты
STANDARD_SECRET_ROOMS = {
    # Практические и полезные
    "Оружейный склад": "В комнате хранится небольшой арсенал оружия и боеприпасов для защиты бункера.",
    "Медицинский склад": "Запасы медикаментов, хирургических инструментов и медицинского оборудования.",
    "Мастерская с инструментами": "Полностью оборудованная мастерская для ремонта и создания необходимых предметов.",
    "Склад электроники": "Запасные части и электронные компоненты для поддержания систем бункера.",
    "Гидропонная ферма": "Система выращивания растений без почвы, обеспечивающая свежую еду.",
    "Химическая лаборатория": "Оборудование для анализа веществ и создания необходимых химических соединений.",
    "3D-фабрика для печати чего угодно": "Современный 3D-принтер с запасом материалов для создания различных предметов.",
    "Универсальная ремонтная станция": "Автоматизированная система для ремонта любого оборудования.",
    "Роботизированный хирургический кабинет": "Автономная медицинская система для сложных операций.",
    
    # Образовательные и информационные
    "Образовательный комплекс": "Библиотека с учебными материалами и образовательными программами.",
    "Архив всего интернета начиная с 2015 года": "Полная копия интернета с огромным объёмом информации.",
    "ИИ-серверная с ограниченным доступом": "Мощный искусственный интеллект для решения сложных задач.",
    "Радиостанция": "Оборудование для связи с внешним миром и поиска выживших.",
    "Комната видеонаблюдения": "Система наблюдения за территорией вокруг бункера.",
    
    # Развлекательные и комфорт
    "Бар": "Запасы алкоголя и место для отдыха и расслабления.",
    "Кинотеатр": "Развлекательная система с большой коллекцией фильмов.",
    "Спортивный зал": "Оборудование для поддержания физической формы.",
    "VR-симулятор на 4 человека": "Система виртуальной реальности для развлечения и обучения.",
    "Бассейн с искусственным солнцем": "Место для плавания и отдыха с имитацией солнечного света.",
    "Музыкальная студия": "Музыкальные инструменты и оборудование для записи.",
    "Комната для медитации": "Тихое место для размышлений и восстановления душевного равновесия.",
    
    # Производственные
    "Столярная мастерская": "Инструменты и материалы для работы с деревом.",
    "Кузнечная мастерская": "Кузнечное оборудование для создания металлических изделий.",
    "Роботизированная кухня": "Автоматизированная система приготовления пищи.",
    "Автономная пивоварня": "Оборудование для производства алкогольных напитков.",
    "Мини-ферма насекомых для еды": "Альтернативный источник белка для выживания.",
    
    # Изоляция и безопасность
    "Герметичный изолятор": "Защищённая комната для изоляции заражённых или опасных предметов.",
    "Проход в секретные тоннели под городом": "Скрытый выход из бункера через подземные туннели.",
    "Камера криоконсервации людей": "Технология заморозки для длительного хранения людей.",
    "Центр управления турелями над бункером": "Система автоматической защиты бункера."
}

# Стандартные комнаты бункера
STANDARD_BUNKER_ROOMS = [
    "Кухня", "Спальные комнаты", "Столовая", "Санузел", "Кладовая", 
    "Генераторная", "Система вентиляции", "Медпункт", "Радиорубка"
]

def generate_player_cards(allow_hidden_roles: bool = True) -> Dict[str, str]:
    """Генерирует набор карт для игрока"""
    gender = random.choice(["Мужской", "Женский"])
    age = random.randint(18, 65)
    
    # Генерируем ФИО в зависимости от пола
    if gender == "Мужской":
        full_name = fake.name_male()
    else:
        full_name = fake.name_female()
    
    cards = {
        "profession": random.choice(PROFESSIONS),
        "health": random.choice(HEALTH_STATUSES),
        "age": str(age),
        "gender": gender,
        "full_name": full_name,
        "skill": random.choice(SKILLS),
        "baggage": random.choice(BAGGAGE),
        "phobia": random.choice(PHOBIAS),
        "additional_info": random.choice(ADDITIONAL_INFO),
        "hidden_role": "Нет" # По умолчанию нет скрытой роли
    }

    if allow_hidden_roles and random.random() < 0.3: # 30% шанс получить скрытую роль
        cards["hidden_role"] = random.choice(HIDDEN_ROLES)
    
    return cards

class JoinButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤПрисоединитьсяㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ", style=discord.ButtonStyle.green)
    async def join_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == interaction.guild_id,
                        BunkerGame.status == BunkerGameStatusENUM.LOBBY.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.followup.send("Сейчас нет активной игры в лобби!", ephemeral=True)
                return
            
            # Проверяем, не в игре ли уже игрок
            existing_player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.user_id == interaction.user.id
                    )
                )
            )
            if existing_player.scalar_one_or_none():
                await interaction.followup.send("Вы уже в игре!", ephemeral=True)
                return
            
            # Проверяем вместимость бункера
            players = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.game_id == game.id)
            )
            if len(players.scalars().all()) >= game.bunker_capacity:
                await interaction.followup.send("Бункер уже заполнен!", ephemeral=True)
                return
            
            # Добавляем игрока
            player = BunkerPlayer(
                game_id=game.id,
                user_id=interaction.user.id
            )
            session.add(player)
            await session.commit()
        
        # Уведомляем об этом в основном чате
        main_channel = interaction.client.get_channel(game.announcements_text_channel_id)
        if main_channel:
            embeds = get_embeds("bunker/player_joined",
                playerName=interaction.user.display_name
            )
            await main_channel.send(embeds=embeds)
            
            # Обновляем эмбед лобби
            await self.cog.update_lobby_embed(game.id)
        
        await interaction.followup.send("Вы присоединились к игре!", ephemeral=True)

class VotingView(discord.ui.View):
    """UI для голосования в личных сообщениях"""
    
    def __init__(self, game_id: int, voter_id: int, round_number: int, target_players: List[BunkerPlayer], bot):
        super().__init__(timeout=300)  # 5 минут на голосование
        self.game_id = game_id
        self.voter_id = voter_id
        self.round_number = round_number
        self.bot = bot
        
        # Добавляем user select для голосования
        user_select = discord.ui.UserSelect(
            placeholder="Выберите игрока для изгнания из бункера",
            min_values=1,
            max_values=1,
            custom_id=f"bunker_vote_{game_id}_{voter_id}_{round_number}"
        )
        
        async def user_select_callback(interaction: discord.Interaction):
            if interaction.user.id != self.voter_id:
                await interaction.response.send_message("❌ Это не ваше голосование!", ephemeral=True)
                return
            
            selected_user = interaction.data['values'][0] if interaction.data['values'] else None
            if not selected_user:
                await interaction.response.send_message("❌ Не выбран игрок!", ephemeral=True)
                return
            
            await self.process_vote(interaction, int(selected_user))
        
        user_select.callback = user_select_callback
        self.add_item(user_select)
    
    async def process_vote(self, interaction: discord.Interaction, target_user_id: int):
        """Обрабатывает голос игрока"""
        async with get_async_session() as session:
            # Проверяем, что игра еще идет
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.id == self.game_id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value,
                        BunkerGame.current_round == self.round_number
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.response.send_message("❌ Голосование уже завершено!", ephemeral=True)
                return
            
            # Находим игрока-избирателя
            voter_player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == self.game_id,
                        BunkerPlayer.user_id == self.voter_id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            voter_player = voter_player.scalar_one_or_none()
            
            if not voter_player:
                await interaction.response.send_message("❌ Вы не можете голосовать!", ephemeral=True)
                return
            
            # Находим цель голосования по user_id
            target_player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == self.game_id,
                        BunkerPlayer.user_id == target_user_id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            target_player = target_player.scalar_one_or_none()
            
            if not target_player:
                await interaction.response.send_message("❌ Недопустимая цель для голосования!", ephemeral=True)
                return
            
            # Проверяем, не голосует ли игрок за себя
            if target_player.user_id == self.voter_id:
                await interaction.response.send_message("❌ Нельзя голосовать за себя!", ephemeral=True)
                return
            
            # Проверяем, не голосовал ли уже этот игрок в этом раунде
            existing_vote = await session.execute(
                select(BunkerGameLog).where(
                    and_(
                        BunkerGameLog.game_id == self.game_id,
                        BunkerGameLog.round_number == self.round_number,
                        BunkerGameLog.actor_player_id == voter_player.id,
                        BunkerGameLog.action_type == BunkerActionTypeENUM.VOTE_CAST.value
                    )
                )
            )
            if existing_vote.scalar_one_or_none():
                await interaction.response.send_message("❌ Вы уже проголосовали в этом раунде!", ephemeral=True)
                return
            
            # Логируем голос
            log = BunkerGameLog(
                game_id=self.game_id,
                round_number=self.round_number,
                actor_player_id=voter_player.id,
                target_player_id=target_player.id,
                action_type=BunkerActionTypeENUM.VOTE_CAST.value,
                action_details={"target_user_id": target_user_id}
            )
            session.add(log)
            await session.commit()
            
            target_user = self.bot.get_user(target_user_id)
            target_name = target_user.display_name if target_user else "Неизвестный игрок"
            
            await interaction.response.send_message(
                f"✅ Ваш голос за **{target_name}** принят!", 
                ephemeral=True
            )
            
            # Отключаем view после голосования
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(view=self)

class BunkerCog(discord.Cog):
    """Игра Бункер - выживание в постапокалипсисе"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, BunkerGame] = {}  # game_id -> game
        
    async def cog_load(self):
        """Загрузка кога и восстановление активных игр"""
        logger.info("Загрузка кога Бункер...")
        
        # TODO: Восстановление активных игр из БД
        
    bunker_group = discord.SlashCommandGroup("bunker")
    leader_group = bunker_group.create_subgroup("leader", "Команды для ведущего игры")
    
    @bunker_group.command(name="create")
    @app_commands.describe(
        capacity="Вместимость бункера (по умолчанию 10)",
        catastrophe="Тип катастрофы (по умолчанию случайная)"
    )
    async def bunker_create(self, ctx: discord.ApplicationContext, capacity: Optional[int] = 10, catastrophe: Optional[str] = None):
        """Создать новую игру Бункер"""
        await ctx.defer(ephemeral=True)
        
        if ctx.guild is None:
            await ctx.followup.send("❌ Эта команда может быть использована только на сервере!", ephemeral=True)
            return
            
        # Проверка на существующую игру
        async with get_async_session() as session:
            stmt = select(BunkerGame).where(
                and_(
                    BunkerGame.guild_id == ctx.guild.id,
                    BunkerGame.status.in_([BunkerGameStatusENUM.LOBBY.value, BunkerGameStatusENUM.RUNNING.value])
                )
            )
            result = await session.execute(stmt)
            existing_game = result.scalar_one_or_none()
            
            if existing_game:
                await ctx.followup.send("❌ На этом сервере уже есть активная игра Бункер!", ephemeral=True)
                return
                
            # Генерируем катастрофу
            if catastrophe and catastrophe in CATASTROPHES:
                catastrophe_data = CATASTROPHES[catastrophe]
                catastrophe_info = {
                    "name": catastrophe,
                    "description": catastrophe_data["description"],
                    "survival_years": random.randint(*catastrophe_data["survival_years"]),
                    "special_rooms": catastrophe_data["special_rooms"]
                }
            else:
                catastrophe_info = self.generate_catastrophe()
            
            # Генерируем информацию о бункере
            bunker_info = self.generate_bunker_info()
            
            # Генерируем секретную комнату (если включена настройка)
            secret_room = None
            if random.random() < 0.7:  # 70% шанс на секретную комнату
                secret_room = self.generate_secret_room(catastrophe_info["special_rooms"])
                
            # Создание категории и каналов
            category = await ctx.guild.create_category("🎮 Бункер")
            
            # Создание каналов
            main_voice = await category.create_voice_channel("🎮 Основной")
            announcements = await category.create_text_channel("📢 Объявления")
            player_cards = await category.create_text_channel("🎴 Карты игроков")
            wasteland = await category.create_voice_channel("🗑 Пустошь")
            logs = await category.create_text_channel("📝 Логи")
            
            # Создание игры в БД
            new_game = BunkerGame(
                guild_id=ctx.guild.id,
                category_channel_id=category.id,
                main_voice_channel_id=main_voice.id,
                announcements_text_channel_id=announcements.id,
                player_cards_text_channel_id=player_cards.id,
                wasteland_voice_channel_id=wasteland.id,
                log_text_channel_id=logs.id,
                leader_id=ctx.author.id,
                status=BunkerGameStatusENUM.LOBBY.value,
                bunker_capacity=capacity,
                catastrophe_type=catastrophe_info["name"],
                survival_duration_years=catastrophe_info["survival_years"],
                bunker_total_area_sqm=bunker_info["area"],
                bunker_known_rooms={"rooms": bunker_info["known_rooms"]},
                secret_room_details=secret_room if secret_room else None,
                game_settings={
                    "active_card_pools": ["default"],
                    "round_timer": 300,  # 5 минут
                    "vote_timer": 60,    # 1 минута
                    "allow_hidden_roles": True,
                    "allow_dynamic_events": True,
                    "secret_room_enabled": secret_room is not None,
                    "secret_room_opens_round": 3 if secret_room else None,
                    "catastrophe_description": catastrophe_info["description"]
                }
            )
            
            session.add(new_game)
            await session.commit()
            
            # Создание эмбеда лобби
            known_rooms_str = ", ".join(bunker_info["known_rooms"])
            embeds = get_embeds("bunker/game_created",
                capacity=capacity,
                catastrophe=catastrophe_info["name"],
                survivalYears=catastrophe_info["survival_years"],
                bunkerArea=bunker_info["area"],
                knownRooms=known_rooms_str,
                creatorName=ctx.author.display_name,
                playersList="Пока никого нет"
            )
            
            # Создание кнопок управления
            view = JoinButton()
            
            # Отправка сообщения с лобби
            message = await announcements.send(embeds=embeds, view=view)
            
            # Сохранение ID сообщения
            new_game.lobby_message_id = message.id
            await session.commit()
            
            # Добавление создателя игры как первого игрока
            player = BunkerPlayer(
                game_id=new_game.id,
                user_id=ctx.author.id
            )
            session.add(player)
            await session.commit()
            
            # Обновление эмбеда
            await self.update_lobby_embed(new_game.id)
            
            secret_room_text = f"\n🚪 Секретная комната: {secret_room['name']}" if secret_room else ""
            await ctx.followup.send(f"✅ Игра Бункер создана! Перейдите в канал {announcements.mention}\n" +
                                  f"🌍 Катастрофа: {catastrophe_info['name']}\n" +
                                  f"⏱️ Срок выживания: {catastrophe_info['survival_years']} лет\n" +
                                  f"🏠 Площадь бункера: {bunker_info['area']} кв.м{secret_room_text}", ephemeral=True)

    async def update_lobby_embed(self, game_id: int):
        """Обновление эмбеда лобби"""
        async with get_async_session() as session:
            stmt = select(BunkerGame).where(BunkerGame.id == game_id)
            result = await session.execute(stmt)
            game = result.scalar_one_or_none()
            
            if not game:
                return
                
            # Получение списка игроков
            stmt = select(BunkerPlayer).where(BunkerPlayer.game_id == game_id)
            result = await session.execute(stmt)
            players = result.scalars().all()
            
            # Получение информации об игроках
            player_list = []
            for player in players:
                user = self.bot.get_user(player.user_id)
                if user:
                    player_list.append(f"• {user.mention}")
            
            # Обновление эмбеда
            channel = self.bot.get_channel(game.announcements_text_channel_id)
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(game.lobby_message_id)
            except discord.NotFound:
                return
                
            embed = message.embeds[0]
            embed.set_field_at(
                1,
                name="👥 Игроки",
                value="\n".join(player_list) if player_list else "Пока никого нет",
                inline=False
            )
            
            await message.edit(embed=embed)

    @bunker_group.command(name="join")
    async def bunker_join(self, ctx: discord.ApplicationContext):
        """Присоединиться к игре Бункер"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.status == BunkerGameStatusENUM.LOBBY.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("Сейчас нет активной игры в лобби!", ephemeral=True)
                return
            
            # Проверяем, не в игре ли уже игрок
            existing_player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.user_id == ctx.author.id
                    )
                )
            )
            if existing_player.scalar_one_or_none():
                await ctx.followup.send("Вы уже в игре!", ephemeral=True)
                return
            
            # Проверяем вместимость бункера
            players = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.game_id == game.id)
            )
            if len(players.scalars().all()) >= game.bunker_capacity:
                await ctx.followup.send("Бункер уже заполнен!", ephemeral=True)
                return
            
            # Добавляем игрока
            player = BunkerPlayer(
                game_id=game.id,
                user_id=ctx.author.id
            )
            session.add(player)
            await session.commit()
        
        # Уведомляем об этом в основном чате
        main_channel = self.bot.get_channel(game.announcements_text_channel_id)
        if main_channel:
            embeds = get_embeds("bunker/player_joined",
                playerName=ctx.author.display_name
            )
            await main_channel.send(embeds=embeds)
            
            # Обновляем эмбед лобби
            await self.update_lobby_embed(game.id)
        
        await ctx.followup.send("Вы присоединились к игре!", ephemeral=True)

    async def start_game(self, game: BunkerGame):
        """Запускает игру и раздает карты"""
        async with get_async_session() as session:
            # Получаем список игроков
            players = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.game_id == game.id)
            )
            players = players.scalars().all()
            
            # Обновляем статус игры
            game.status = BunkerGameStatusENUM.RUNNING.value
            game.start_time = int(datetime.now().timestamp())
            game.current_round = 1
            await session.commit()
            
            # Получаем каналы
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            player_cards_channel = self.bot.get_channel(game.player_cards_text_channel_id)
            
            # Отправляем сообщение о начале игры с расширенной информацией
            known_rooms_str = ", ".join(game.bunker_known_rooms.get("rooms", []) if game.bunker_known_rooms else ["Неизвестно"])
            catastrophe_description = game.game_settings.get("catastrophe_description", "Неизвестная катастрофа")
            
            embeds = get_embeds("bunker/catastrophe_intro",
                catastropheType=game.catastrophe_type,
                catastropheDescription=catastrophe_description,
                survivalYears=game.survival_duration_years or "Неизвестно",
                bunkerCapacity=game.bunker_capacity,
                bunkerArea=game.bunker_total_area_sqm or "Неизвестно",
                knownRooms=known_rooms_str
            )
            await announcements_channel.send(embeds=embeds)
            
            # Раздаем карты каждому игроку
            for player in players:
                user = self.bot.get_user(player.user_id)
                if not user:
                    continue
                
                # Генерируем карты для игрока
                cards = generate_player_cards(
                    allow_hidden_roles=game.game_settings.get("allow_hidden_roles", True)
                )
                
                # Сохраняем карты в БД
                for card_type, card_value in cards.items():
                    card = BunkerPlayerCard(
                        player_id=player.id,
                        card_type=BunkerCardTypeENUM[card_type.upper()].value,
                        card_name=card_value,
                        is_hidden=card_type in ["phobia", "additional_info", "health"]
                    )
                    session.add(card)
                
                # Отправляем карты игроку в ЛС
                embeds = get_embeds("bunker/player_cards_dm",
                    playerName=user.display_name,
                    professionName=cards["profession"],
                    healthStatus=cards["health"],
                    age=cards["age"],
                    gender=cards["gender"],
                    fullName=cards["full_name"],
                    skillName=cards["skill"],
                    itemName=cards["baggage"],
                    traitName=cards["phobia"],
                    extraInfo=cards["additional_info"],
                    hiddenRole=cards["hidden_role"]
                )
                try:
                    await user.send(embeds=embeds)
                except discord.Forbidden:
                    await announcements_channel.send(f"{user.mention}, я не могу отправить вам карты в личные сообщения! Пожалуйста, включите личные сообщения от участников сервера.")
                
                # Создаем эмбед с картами игрока в канале карт
                embeds = get_embeds("bunker/player_card",
                    playerName=user.display_name,
                    professionName=cards["profession"],
                    healthStatus="Скрыто",
                    age=cards["age"],
                    gender=cards["gender"],
                    fullName=cards["full_name"],
                    skillName=cards["skill"],
                    itemName=cards["baggage"],
                    traitName="Скрыто",
                    extraInfo="Скрыто",
                    hiddenRole="Скрыто"
                )
                message = await player_cards_channel.send(embeds=embeds)
                
                # Сохраняем ID сообщения с картами
                player.cards_message_id = message.id
                
                # Меняем никнейм игрока
                try:
                    await user.edit(nick=f"Игрок №{player.id}")
                except discord.Forbidden:
                    await announcements_channel.send(f"Я не могу изменить никнейм {user.mention}. Пожалуйста, дайте мне права на управление никнеймами.")
            
            await session.commit()
            
            # Отправляем сообщение о начале первого раунда
            alive_players = [p for p in players if not p.is_expelled]
            available_spots = game.bunker_capacity - len(alive_players)
            embeds = get_embeds("bunker/round_start_discussion",
                roundNumber=game.current_round,
                discussionTimeLimit=game.game_settings.get("round_timer", 300),
                alivePlayersCount=len(alive_players),
                availableSpots=available_spots
            )
            await announcements_channel.send(embeds=embeds)
            
            # Если есть секретная комната, отправим сообщение о том, что она будет открыта позже
            if game.secret_room_details:
                secret_room_round = game.game_settings.get("secret_room_opens_round", 3)
                await announcements_channel.send(f"🔒 В бункере есть секретная комната, которая откроется на {secret_room_round}-м раунде...")
            
            # Логируем начало игры
            log = BunkerGameLog(
                game_id=game.id,
                round_number=game.current_round,
                action_type=BunkerActionTypeENUM.GAME_START.value,
                action_details={"players_count": len(players)}
            )
            session.add(log)
            await session.commit()

    @leader_group.command(name="start")
    async def bunker_start(self, ctx: discord.ApplicationContext):
        """Начать игру Бункер"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.status == BunkerGameStatusENUM.LOBBY.value,
                        BunkerGame.leader_id == ctx.author.id
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для начала игры или игра не найдена!", ephemeral=True)
                return
            
            # Получаем список игроков
            players = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.game_id == game.id)
            )
            players = players.scalars().all()
            
            if len(players) < 3:
                await ctx.followup.send("Для начала игры нужно минимум 3 игрока!", ephemeral=True)
                return
            
            # Запускаем игру
            await self.start_game(game)
            
            await ctx.followup.send("✅ Игра началась!", ephemeral=True)

    @leader_group.command(name="end")
    async def bunker_end(self, ctx: discord.ApplicationContext):
        """Завершить игру Бункер"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права и статус игры
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status.in_([
                            BunkerGameStatusENUM.RUNNING.value,
                            BunkerGameStatusENUM.LOBBY.value
                        ])
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для завершения игры или игра не найдена!", ephemeral=True)
                return
            
            # Обновляем статус игры
            game.status = BunkerGameStatusENUM.FINISHED.value
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
                        name=f"Бункер-{game.id}-{datetime.now().strftime('%Y%m%d')}"
                    )
            
            # Удаляем все игровые каналы кроме логов
            if game.announcements_text_channel_id:
                main_channel = self.bot.get_channel(game.announcements_text_channel_id)
                if main_channel:
                    await main_channel.delete()
            
            if game.main_voice_channel_id:
                voice_channel = self.bot.get_channel(game.main_voice_channel_id)
                if voice_channel:
                    await voice_channel.delete()
            
            if game.player_cards_text_channel_id:
                cards_channel = self.bot.get_channel(game.player_cards_text_channel_id)
                if cards_channel:
                    await cards_channel.delete()
            
            if game.wasteland_voice_channel_id:
                wasteland_channel = self.bot.get_channel(game.wasteland_voice_channel_id)
                if wasteland_channel:
                    await wasteland_channel.delete()
            
            if game.category_channel_id:
                category = self.bot.get_channel(game.category_channel_id)
                if category:
                    await category.delete()
            
            # Отправляем сообщение о завершении в лог
            if logs_channel:
                embeds = get_embeds("bunker/game_end",
                    winnersList="Игра была остановлена ведущим",
                    rounds="0",
                    excluded="0",
                    events="0",
                    playersCards="Статистика недоступна"
                )
                await logs_channel.send(embeds=embeds)

    @leader_group.command(name="secret_room")
    async def bunker_secret_room(self, ctx: discord.ApplicationContext):
        """Открыть секретную комнату"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права и статус игры
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            if not game.secret_room_details:
                await ctx.followup.send("В этой игре нет секретной комнаты!", ephemeral=True)
                return
            
            # Получаем канал объявлений
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            
            # Отправляем сообщение о секретной комнате
            secret_room = game.secret_room_details
            embeds = get_embeds("bunker/secret_room_revealed",
                roomName=secret_room["name"],
                roomDescription=secret_room["description"],
                roundNumber=game.current_round
            )
            await announcements_channel.send(embeds=embeds)
            
            # Логируем открытие секретной комнаты
            log = BunkerGameLog(
                game_id=game.id,
                round_number=game.current_round,
                action_type=BunkerActionTypeENUM.EVENT_TRIGGERED.value,
                action_details={
                    "event_type": "secret_room_revealed",
                    "room_name": secret_room["name"],
                    "room_description": secret_room["description"]
                }
            )
            session.add(log)
            await session.commit()
            
            await ctx.followup.send(f"✅ Секретная комната '{secret_room['name']}' была открыта!", ephemeral=True)

    def generate_catastrophe(self):
        """Генерирует случайную катастрофу"""
        catastrophe_name = random.choice(list(CATASTROPHES.keys()))
        catastrophe_data = CATASTROPHES[catastrophe_name]
        survival_years = random.randint(*catastrophe_data["survival_years"])
        
        return {
            "name": catastrophe_name,
            "description": catastrophe_data["description"],
            "survival_years": survival_years,
            "special_rooms": catastrophe_data["special_rooms"]
        }

    def generate_secret_room(self, catastrophe_special_rooms):
        """Генерирует секретную комнату"""
        # 30% шанс получить специальную комнату для катастрофы
        if catastrophe_special_rooms and random.random() < 0.3:
            room_name = random.choice(catastrophe_special_rooms)
            room_description = f"Специальная комната, связанная с текущей катастрофой: {room_name}"
        else:
            room_name = random.choice(list(STANDARD_SECRET_ROOMS.keys()))
            room_description = STANDARD_SECRET_ROOMS[room_name]
        
        return {
            "name": room_name,
            "description": room_description
        }

    def generate_bunker_info(self):
        """Генерирует информацию о бункере"""
        area = random.randint(200, 800)  # площадь в кв.м.
        room_count = random.randint(3, 6)
        known_rooms = random.sample(STANDARD_BUNKER_ROOMS, room_count)
        
        return {
            "area": area,
            "known_rooms": known_rooms
        }

    @bunker_group.command(name="status")
    async def bunker_status(self, ctx: discord.ApplicationContext):
        """Показать статус текущей игры"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.status.in_([
                            BunkerGameStatusENUM.LOBBY.value,
                            BunkerGameStatusENUM.RUNNING.value
                        ])
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("На сервере нет активной игры Бункер!", ephemeral=True)
                return
            
            # Получаем список игроков
            players = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.game_id == game.id)
            )
            players = players.scalars().all()
            alive_players = [p for p in players if not p.is_expelled]
            
            # Формируем информацию
            status_text = "Лобби" if game.status == BunkerGameStatusENUM.LOBBY.value else "В игре"
            spots_remaining = game.bunker_capacity - len(alive_players)
            known_rooms_str = ", ".join(game.bunker_known_rooms.get("rooms", []) if game.bunker_known_rooms else ["Неизвестно"])
            
            secret_room_text = ""
            if game.secret_room_details:
                secret_room_round = game.game_settings.get("secret_room_opens_round", 3)
                if game.current_round >= secret_room_round:
                    secret_room_text = f"🚪 **Секретная комната:** {game.secret_room_details['name']}"
                else:
                    secret_room_text = f"🔒 **Секретная комната:** Откроется на {secret_room_round}-м раунде"
            
            embed = discord.Embed(
                title="📊 Статус игры Бункер",
                color=3447003 if game.status == BunkerGameStatusENUM.LOBBY.value else 15158332
            )
            
            embed.add_field(name="🌍 Катастрофа", value=game.catastrophe_type, inline=True)
            embed.add_field(name="⏱️ Срок выживания", value=f"{game.survival_duration_years or 'Неизвестно'} лет", inline=True)
            embed.add_field(name="📈 Статус", value=status_text, inline=True)
            
            embed.add_field(name="👥 Игроки в живых", value=f"{len(alive_players)}/{game.bunker_capacity}", inline=True)
            embed.add_field(name="🎯 Текущий раунд", value=str(game.current_round), inline=True)
            embed.add_field(name="🏠 Площадь бункера", value=f"{game.bunker_total_area_sqm or 'Неизвестно'} кв.м", inline=True)
            
            embed.add_field(name="🚪 Известные комнаты", value=known_rooms_str, inline=False)
            
            if secret_room_text:
                embed.add_field(name="🔍 Секретная комната", value=secret_room_text, inline=False)
            
            await ctx.followup.send(embed=embed, ephemeral=True)

    @leader_group.command(name="voting")
    async def bunker_voting(self, ctx: discord.ApplicationContext):
        """Начать голосование за изгнание"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права и статус игры
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("❌ У вас нет прав для управления игрой или игра не найдена!", ephemeral=True)
                return
            
            # Получаем живых игроков
            players = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            players = players.scalars().all()
            
            if len(players) <= game.bunker_capacity:
                await ctx.followup.send("🎉 Голосование не нужно! Все оставшиеся игроки помещаются в бункер!", ephemeral=True)
                return
            
            if len(players) < 2:
                await ctx.followup.send("❌ Для голосования нужно минимум 2 живых игрока!", ephemeral=True)
                return
            
            # Отправляем сообщение о начале голосования в основной канал
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            vote_timer = game.game_settings.get("vote_timer", 60)
            
            embeds = get_embeds("bunker/voting_starts",
                votingTimeLimit=vote_timer,
                roundNumber=game.current_round,
                alivePlayersCount=len(players)
            )
            await announcements_channel.send(embeds=embeds)
            
            # Отправляем UI для голосования каждому игроку в ЛС
            for voter in players:
                voter_user = self.bot.get_user(voter.user_id)
                if not voter_user:
                    continue
                
                # Создаем список всех игроков кроме голосующего для голосования
                target_players = [p for p in players if p.id != voter.id]
                
                if not target_players:
                    continue
                
                # Создаем view для голосования
                view = VotingView(game.id, voter.user_id, game.current_round, target_players, self.bot)
                
                # Создаем эмбед для личного сообщения
                embed = discord.Embed(
                    title="🗳️ Ваш бюллетень для голосования",
                    description=f"Раунд {game.current_round}: Выберите игрока для изгнания из бункера",
                    color=15158332
                )
                embed.add_field(
                    name="⏰ Время на размышление", 
                    value=f"{vote_timer} секунд", 
                    inline=True
                )
                embed.add_field(
                    name="👥 Кандидатов на изгнание", 
                    value=str(len(target_players)), 
                    inline=True
                )
                embed.set_footer(text="Выберите мудро - от вашего решения зависит судьба бункера!")
                
                try:
                    await voter_user.send(embed=embed, view=view)
                except discord.Forbidden:
                    await announcements_channel.send(
                        f"{voter_user.mention}, я не могу отправить вам бюллетень! Откройте ЛС."
                    )
            
            await ctx.followup.send("✅ Голосование началось! Игроки получили бюллетени в ЛС.", ephemeral=True)

    @leader_group.command(name="stop_voting")
    async def bunker_stop_voting(self, ctx: discord.ApplicationContext):
        """Завершить голосование и подсчитать голоса"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("❌ У вас нет прав для управления игрой!", ephemeral=True)
                return
            
            # Получаем все голоса за текущий раунд
            votes = await session.execute(
                select(BunkerGameLog).where(
                    and_(
                        BunkerGameLog.game_id == game.id,
                        BunkerGameLog.round_number == game.current_round,
                        BunkerGameLog.action_type == BunkerActionTypeENUM.VOTE_CAST.value
                    )
                )
            )
            votes = votes.scalars().all()
            
            if not votes:
                await ctx.followup.send("❌ Никто не проголосовал!", ephemeral=True)
                return
            
            # Подсчитываем голоса
            vote_count = {}
            for vote in votes:
                target_id = vote.target_player_id
                if target_id not in vote_count:
                    vote_count[target_id] = 0
                vote_count[target_id] += 1
            
            # Находим игрока с максимальным количеством голосов
            max_votes = max(vote_count.values())
            expelled_candidates = [pid for pid, count in vote_count.items() if count == max_votes]
            
            if len(expelled_candidates) > 1:
                # Ничья - можно реализовать дополнительную логику
                await ctx.followup.send(f"⚖️ Ничья в голосовании! {len(expelled_candidates)} игроков получили по {max_votes} голосов. Требуется переголосование.", ephemeral=True)
                return
            
            # Изгоняем игрока
            expelled_player_id = expelled_candidates[0]
            expelled_player = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.id == expelled_player_id)
            )
            expelled_player = expelled_player.scalar_one_or_none()
            
            if not expelled_player:
                await ctx.followup.send("❌ Ошибка: игрок не найден!", ephemeral=True)
                return
            
            # Обновляем статус игрока
            expelled_player.is_expelled = True
            expelled_player.expulsion_round = game.current_round
            expelled_player.final_status = "expelled_vote"
            
            # Получаем все карты изгнанного игрока
            player_cards = await session.execute(
                select(BunkerPlayerCard).where(BunkerPlayerCard.player_id == expelled_player.id)
            )
            player_cards = player_cards.scalars().all()
            
            # Собираем информацию о картах
            cards_info = {}
            for card in player_cards:
                card_type = card.card_type
                cards_info[card_type] = card.card_name
            
            await session.commit()
            
            # Отправляем сообщение об изгнании
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            expelled_user = self.bot.get_user(expelled_player.user_id)
            
            if expelled_user and announcements_channel:
                # Получаем количество оставшихся игроков
                remaining_players = await session.execute(
                    select(BunkerPlayer).where(
                        and_(
                            BunkerPlayer.game_id == game.id,
                            BunkerPlayer.is_expelled == False
                        )
                    )
                )
                remaining_count = len(remaining_players.scalars().all())
                
                embeds = get_embeds("bunker/player_expelled",
                    expelledPlayerName=expelled_user.display_name,
                    expelledPlayerAvatar=expelled_user.display_avatar.url,
                    votesAgainst=max_votes,
                    totalVotes=len(votes),
                    roundNumber=game.current_round,
                    expelledProfession=cards_info.get("profession", "Неизвестно"),
                    expelledHealth=cards_info.get("health", "Неизвестно"),
                    expelledAge=cards_info.get("age", "Неизвестно"),
                    expelledGender=cards_info.get("gender", "Неизвестно"),
                    expelledFullName=cards_info.get("full_name", "Неизвестно"),
                    expelledSkill=cards_info.get("skill", "Неизвестно"),
                    expelledBaggage=cards_info.get("baggage", "Неизвестно"),
                    expelledPhobia=cards_info.get("phobia", "Неизвестно"),
                    expelledAdditionalInfo=cards_info.get("additional_info", "Неизвестно"),
                    expelledHiddenRole=cards_info.get("hidden_role", "Нет"),
                    remainingPlayers=remaining_count
                )
                await announcements_channel.send(embeds=embeds)
                
                # Переносим изгнанного в канал "Пустошь"
                if expelled_user.voice and expelled_user.voice.channel:
                    wasteland_channel = self.bot.get_channel(game.wasteland_voice_channel_id)
                    if wasteland_channel:
                        try:
                            await expelled_user.move_to(wasteland_channel)
                        except discord.Forbidden:
                            pass
                
                # Меняем никнейм изгнанного
                try:
                    full_name = cards_info.get("full_name", expelled_user.display_name)
                    await expelled_user.edit(nick=f"💀 {full_name}")
                except discord.Forbidden:
                    pass
                
                # Проверяем условие победы
                if remaining_count <= game.bunker_capacity:
                    await self.end_game_victory(game, session)
                
            await ctx.followup.send(f"✅ Голосование завершено! {expelled_user.display_name if expelled_user else 'Игрок'} изгнан из бункера.", ephemeral=True)

    async def end_game_victory(self, game: BunkerGame, session: AsyncSession):
        """Завершает игру победой выживших"""
        game.status = BunkerGameStatusENUM.FINISHED.value
        game.end_time = int(datetime.now().timestamp())
        
        # Получаем выживших
        survivors = await session.execute(
            select(BunkerPlayer).where(
                and_(
                    BunkerPlayer.game_id == game.id,
                    BunkerPlayer.is_expelled == False
                )
            )
        )
        survivors = survivors.scalars().all()
        
        # Отправляем сообщение о победе
        announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
        if announcements_channel:
            survivor_names = []
            for survivor in survivors:
                user = self.bot.get_user(survivor.user_id)
                if user:
                    survivor_names.append(user.display_name)
            
            embed = discord.Embed(
                title="🎉 ДВЕРИ БУНКЕРА ЗАКРЫТЫ!",
                description="Выжившие успешно заперлись в бункере и будут ждать окончания катастрофы!",
                color=3066993
            )
            embed.add_field(
                name="🏆 Победители",
                value="\n".join([f"• {name}" for name in survivor_names]) if survivor_names else "Никого",
                inline=False
            )
            embed.add_field(
                name="📊 Статистика",
                value=f"Раундов сыграно: {game.current_round}\nСрок выживания: {game.survival_duration_years} лет",
                inline=True
            )
            embed.set_footer(text="Игра завершена! Спасибо за участие!")
            
            await announcements_channel.send(embed=embed)
        
        await session.commit()

    @leader_group.command(name="voting_results")
    async def bunker_voting_results(self, ctx: discord.ApplicationContext):
        """Показать промежуточные результаты голосования"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("❌ У вас нет прав для управления игрой!", ephemeral=True)
                return
            
            # Получаем все голоса за текущий раунд
            votes = await session.execute(
                select(BunkerGameLog).where(
                    and_(
                        BunkerGameLog.game_id == game.id,
                        BunkerGameLog.round_number == game.current_round,
                        BunkerGameLog.action_type == BunkerActionTypeENUM.VOTE_CAST.value
                    )
                )
            )
            votes = votes.scalars().all()
            
            # Получаем всех живых игроков
            players = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            players = players.scalars().all()
            
            # Подсчитываем голоса
            vote_count = {}
            voters = set()
            for vote in votes:
                target_id = vote.target_player_id
                if target_id not in vote_count:
                    vote_count[target_id] = 0
                vote_count[target_id] += 1
                voters.add(vote.actor_player_id)
            
            # Создаем эмбед с результатами
            embed = discord.Embed(
                title="📊 Промежуточные результаты голосования",
                description=f"Раунд {game.current_round}",
                color=15158332
            )
            
            # Показываем кто за кого голосовал
            results_text = ""
            for player_id, count in sorted(vote_count.items(), key=lambda x: x[1], reverse=True):
                player = next((p for p in players if p.id == player_id), None)
                if player:
                    user = self.bot.get_user(player.user_id)
                    if user:
                        results_text += f"**{user.display_name}**: {count} голос(ов)\n"
            
            if not results_text:
                results_text = "Пока никто не проголосовал"
            
            embed.add_field(name="🗳️ Результаты", value=results_text, inline=False)
            embed.add_field(
                name="📈 Статистика", 
                value=f"Проголосовало: {len(voters)}/{len(players)}", 
                inline=True
            )
            
            await ctx.followup.send(embed=embed, ephemeral=True)

    @leader_group.command(name="next_round")
    async def bunker_next_round(self, ctx: discord.ApplicationContext):
        """Начать следующий раунд обсуждения"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Проверяем права
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.leader_id == ctx.author.id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("❌ У вас нет прав для управления игрой!", ephemeral=True)
                return
            
            # Получаем живых игроков
            players = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            players = players.scalars().all()
            
            if len(players) <= game.bunker_capacity:
                await ctx.followup.send("🎉 Игра уже завершена! Все оставшиеся игроки выжили!", ephemeral=True)
                return
            
            # Увеличиваем номер раунда
            game.current_round += 1
            await session.commit()
            
            # Отправляем сообщение о новом раунде
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            available_spots = game.bunker_capacity
            
            embeds = get_embeds("bunker/round_start_discussion",
                roundNumber=game.current_round,
                discussionTimeLimit=game.game_settings.get("round_timer", 300),
                alivePlayersCount=len(players),
                availableSpots=available_spots
            )
            await announcements_channel.send(embeds=embeds)
            
            # Проверяем, нужно ли открыть секретную комнату
            secret_room_round = game.game_settings.get("secret_room_opens_round", 3)
            if (game.secret_room_details and 
                game.current_round >= secret_room_round and 
                secret_room_round > 0):
                
                # Открываем секретную комнату автоматически
                secret_room = game.secret_room_details
                embeds = get_embeds("bunker/secret_room_revealed",
                    roomName=secret_room["name"],
                    roomDescription=secret_room["description"],
                    roundNumber=game.current_round
                )
                await announcements_channel.send(embeds=embeds)
                
                # Отмечаем, что комната уже была открыта
                settings = game.game_settings.copy()
                settings["secret_room_opens_round"] = 0  # Отключаем автооткрытие
                game.game_settings = settings
                await session.commit()
                
                # Логируем открытие
                log = BunkerGameLog(
                    game_id=game.id,
                    round_number=game.current_round,
                    action_type=BunkerActionTypeENUM.EVENT_TRIGGERED.value,
                    action_details={
                        "event_type": "secret_room_revealed",
                        "room_name": secret_room["name"],
                        "room_description": secret_room["description"]
                    }
                )
                session.add(log)
                await session.commit()
            
            await ctx.followup.send(f"✅ Начался раунд {game.current_round}!", ephemeral=True)

    @bunker_group.command(name="reveal")
    @app_commands.describe(
        card_type="Тип карты для раскрытия",
        card_value="Значение карты (если отличается от того, что у вас)"
    )
    async def bunker_reveal(self, ctx: discord.ApplicationContext, 
                           card_type: discord.Option(str, choices=[
                               "profession", "health", "age", "gender", "full_name", 
                               "skill", "baggage", "phobia", "additional_info", "hidden_role"
                           ]),
                           card_value: Optional[str] = None):
        """Раскрыть одну из своих карт"""
        await ctx.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Ищем активную игру
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.guild_id == ctx.guild_id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await ctx.followup.send("❌ Активная игра не найдена!", ephemeral=True)
                return
            
            # Ищем игрока
            player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.user_id == ctx.author.id,
                        BunkerPlayer.is_expelled == False
                    )
                )
            )
            player = player.scalar_one_or_none()
            
            if not player:
                await ctx.followup.send("❌ Вы не участвуете в игре или уже изгнаны!", ephemeral=True)
                return
            
            # Ищем карту игрока
            card = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == player.id,
                        BunkerPlayerCard.card_type == card_type.upper()
                    )
                )
            )
            card = card.scalar_one_or_none()
            
            if not card:
                await ctx.followup.send("❌ У вас нет такой карты!", ephemeral=True)
                return
            
            if card.is_revealed:
                await ctx.followup.send("❌ Эта карта уже была раскрыта!", ephemeral=True)
                return
            
            # Раскрываем карту
            card.is_revealed = True
            if card_value:
                card.card_name = card_value
            
            await session.commit()
            
            # Отправляем сообщение в основной канал
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            
            card_type_names = {
                "profession": "Профессия",
                "health": "Здоровье", 
                "age": "Возраст",
                "gender": "Пол",
                "full_name": "Имя и Фамилия",
                "skill": "Навык",
                "baggage": "Багаж",
                "phobia": "Фобия",
                "additional_info": "Дополнительная информация",
                "hidden_role": "Скрытая роль"
            }
            
            embed = discord.Embed(
                title="🃏 КАРТА РАСКРЫТА!",
                description=f"{ctx.author.display_name} раскрыл свою карту",
                color=3447003
            )
            embed.add_field(
                name=f"📋 {card_type_names.get(card_type, card_type.title())}",
                value=f"**{card.card_name}**",
                inline=False
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
            await announcements_channel.send(embed=embed)
            
            # Логируем раскрытие карты
            log = BunkerGameLog(
                game_id=game.id,
                round_number=game.current_round,
                actor_player_id=player.id,
                action_type=BunkerActionTypeENUM.CARD_REVEALED.value,
                action_details={
                    "card_type": card_type,
                    "card_value": card.card_name
                }
            )
            session.add(log)
            await session.commit()
            
            # Если раскрыто имя и фамилия, меняем никнейм
            if card_type == "full_name":
                try:
                    await ctx.author.edit(nick=card.card_name)
                except discord.Forbidden:
                    pass
            
            await ctx.followup.send(f"✅ Карта '{card_type_names.get(card_type, card_type)}' раскрыта!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BunkerCog(bot)) 