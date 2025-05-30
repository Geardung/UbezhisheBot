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

# Карты действий с их эффектами
ACTION_CARDS = {
    "Смена реальности": {
        "description": "Все игроки получают новую случайную характеристику выбранного типа",
        "effect_type": "change_all_players",
        "targets": "all",
        "can_choose_card_type": True,
        "activation": "any_time",
        "rarity": "rare"
    },
    "Обмен": {
        "description": "Два игрока обмениваются одной выбранной характеристикой",
        "effect_type": "swap_cards", 
        "targets": "two_players",
        "can_choose_card_type": True,
        "activation": "any_time",
        "rarity": "common"
    },
    "Раскрытие тайны": {
        "description": "Заставить одного игрока немедленно раскрыть одну из скрытых карт",
        "effect_type": "force_reveal",
        "targets": "one_player",
        "can_choose_card_type": False,
        "activation": "any_time", 
        "rarity": "common"
    },
    "Защитный купол": {
        "description": "Дает иммунитет от изгнания на одно голосование",
        "effect_type": "immunity",
        "targets": "one_player",
        "can_choose_card_type": False,
        "activation": "before_vote",
        "rarity": "rare"
    },
    "Саботаж": {
        "description": "Вызывает негативное событие в бункере",
        "effect_type": "trigger_event",
        "targets": "none",
        "can_choose_card_type": False,
        "activation": "any_time",
        "rarity": "uncommon"
    },
    "Дополнительное место": {
        "description": "Увеличивает вместимость бункера на 1",
        "effect_type": "increase_capacity",
        "targets": "none", 
        "can_choose_card_type": False,
        "activation": "any_time",
        "rarity": "epic"
    },
    "Общая амнезия": {
        "description": "Одна характеристика у всех игроков заменяется на новую случайную",
        "effect_type": "replace_all_cards",
        "targets": "all",
        "can_choose_card_type": True,
        "activation": "any_time",
        "rarity": "uncommon"
    },
    "Целитель": {
        "description": "Улучшает здоровье выбранного игрока до 'Отличного'",
        "effect_type": "heal_player",
        "targets": "one_player", 
        "can_choose_card_type": False,
        "activation": "any_time",
        "rarity": "uncommon"
    },
    "Болезнь": {
        "description": "Ухудшает здоровье выбранного игрока",
        "effect_type": "sicken_player",
        "targets": "one_player",
        "can_choose_card_type": False,
        "activation": "any_time",
        "rarity": "uncommon"
    },
    "Хакер": {
        "description": "Позволяет подсмотреть все карты выбранного игрока",
        "effect_type": "peek_cards",
        "targets": "one_player",
        "can_choose_card_type": False,
        "activation": "any_time",
        "rarity": "rare"
    }
}

# События бункера
BUNKER_EVENTS = {
    "Проблемы с электричеством": {
        "description": "Генератор дает сбои! Нужен инженер или электрик для ремонта, иначе все системы жизнеобеспечения будут работать нестабильно.",
        "severity": "medium",
        "required_professions": ["Инженер", "Электрик"],
        "consequences": "Ухудшение условий жизни"
    },
    "Утечка радиации": {
        "description": "Обнаружена утечка радиации в одном из отсеков! Требуется немедленная изоляция зоны и ремонт защитных систем.",
        "severity": "high",
        "required_professions": ["Инженер", "Военный", "Учёный"],
        "consequences": "Угроза здоровью всех жителей"
    },
    "Нехватка еды": {
        "description": "Запасы продовольствия на исходе быстрее, чем планировалось. Нужно найти способ увеличить производство пищи.",
        "severity": "medium", 
        "required_professions": ["Повар", "Учёный"],
        "consequences": "Голод и ослабление организма"
    },
    "Проблемы с водой": {
        "description": "Система очистки воды засорилась. Без ремонта качество воды будет ухудшаться.",
        "severity": "high",
        "required_professions": ["Инженер", "Врач"],
        "consequences": "Отравление и болезни"
    },
    "Психологический кризис": {
        "description": "Длительное пребывание в замкнутом пространстве сказывается на психике жителей. Растет напряженность и конфликты.",
        "severity": "medium",
        "required_professions": ["Психолог", "Учитель", "Актёр"],
        "consequences": "Снижение морали и сплоченности"
    },
    "Пожар": {
        "description": "В одной из комнат начался пожар! Нужно быстро его потушить и восстановить поврежденные системы.",
        "severity": "high",
        "required_professions": ["Военный", "Инженер"],
        "consequences": "Повреждение систем и потеря ресурсов"
    },
    "Заболевание": {
        "description": "Один из жителей серьезно заболел и нуждается в медицинской помощи. Болезнь может быть заразной.",
        "severity": "medium",
        "required_professions": ["Врач"],
        "consequences": "Распространение болезни"
    },
    "Поломка систем связи": {
        "description": "Системы связи с внешним миром вышли из строя. Нужен ремонт, чтобы получать информацию о ситуации снаружи.",
        "severity": "low",
        "required_professions": ["Инженер", "Программист"],
        "consequences": "Изоляция от внешнего мира"
    },
    "Нападение извне": {
        "description": "К бункеру приближается группа вооруженных людей! Нужно решить, как обеспечить защиту.",
        "severity": "high", 
        "required_professions": ["Военный", "Юрист"],
        "consequences": "Угроза безопасности бункера"
    },
    "Депрессия жителей": {
        "description": "Жители бункера впадают в уныние из-за безнадежности ситуации. Нужно поднять моральный дух.",
        "severity": "low",
        "required_professions": ["Психолог", "Актёр", "Учитель"],
        "consequences": "Снижение продуктивности и мотивации"
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

def generate_action_card() -> str:
    """Генерирует случайную карту действия с учетом редкости"""
    # Создаем weighted список для редкости
    weighted_cards = []
    for card_name, card_info in ACTION_CARDS.items():
        rarity = card_info.get("rarity", "common")
        if rarity == "common":
            weight = 4
        elif rarity == "uncommon":
            weight = 2
        elif rarity == "rare":
            weight = 1
        elif rarity == "epic":
            weight = 0.5
        else:
            weight = 1
        
        # Добавляем карту в список нужное количество раз
        for _ in range(int(weight * 10)):
            weighted_cards.append(card_name)
    
    return random.choice(weighted_cards)

def generate_random_event() -> Dict[str, any]:
    """Генерирует случайное событие для бункера"""
    event_name = random.choice(list(BUNKER_EVENTS.keys()))
    event_info = BUNKER_EVENTS[event_name].copy()
    event_info["name"] = event_name
    return event_info

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

class CardRevealView(discord.ui.View):
    """UI для раскрытия карт игрока в личных сообщениях"""
    
    def __init__(self, player_id: int, game_id: int, cards: Dict[str, str], bot):
        super().__init__(timeout=None)  # Никогда не истекает
        self.player_id = player_id
        self.game_id = game_id
        self.cards = cards
        self.bot = bot
        
        # Создаем кнопки для каждой карты
        self.create_buttons()
    
    def create_buttons(self):
        """Создает кнопки для раскрытия карт"""
        # Первый ряд - основные характеристики
        self.add_item(self.create_card_button("profession", "👨‍💼 Профессия", 0))
        self.add_item(self.create_card_button("health", "❤️ Здоровье", 0))
        self.add_item(self.create_card_button("age", "🎂 Возраст", 0))
        self.add_item(self.create_card_button("gender", "⚧️ Пол", 0))
        
        # Второй ряд - личная информация
        self.add_item(self.create_card_button("full_name", "📛 Имя", 1))
        self.add_item(self.create_card_button("skill", "🛠️ Навык", 1))
        self.add_item(self.create_card_button("baggage", "🎒 Багаж", 1))
        
        # Третий ряд - скрытые карты
        self.add_item(self.create_card_button("phobia", "👻 Фобия", 2))
        self.add_item(self.create_card_button("additional_info", "📜 Доп. инфо", 2))
        self.add_item(self.create_card_button("hidden_role", "🎭 Скр. роль", 2))
    
    def create_card_button(self, card_type: str, label: str, row: int):
        """Создает кнопку для конкретной карты"""
        button = discord.ui.Button(
            label=label,
            custom_id=f"reveal_{self.game_id}_{self.player_id}_{card_type}",
            style=discord.ButtonStyle.secondary,
            row=row
        )
        
        async def button_callback(interaction: discord.Interaction):
            await self.reveal_card(interaction, card_type)
        
        button.callback = button_callback
        return button
    
    async def reveal_card(self, interaction: discord.Interaction, card_type: str):
        """Обрабатывает раскрытие карты"""
        # Проверяем, что это правильный игрок
        async with get_async_session() as session:
            player = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.id == self.player_id)
            )
            player = player.scalar_one_or_none()
            
            if not player or player.user_id != interaction.user.id:
                await interaction.response.send_message("❌ Это не ваши карты!", ephemeral=True)
                return
            
            # Проверяем статус игры
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.id == self.game_id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.response.send_message("❌ Игра не активна!", ephemeral=True)
                return
            
            # Ищем карту игрока
            card = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == self.player_id,
                        BunkerPlayerCard.card_type == card_type  # Используем строку
                    )
                )
            )
            card = card.scalar_one_or_none()
            
            if not card:
                await interaction.response.send_message("❌ Карта не найдена!", ephemeral=True)
                return
            
            if card.is_revealed:
                await interaction.response.send_message("❌ Эта карта уже раскрыта!", ephemeral=True)
                return
            
            # Раскрываем карту
            card.is_revealed = True
            await session.commit()
            
            # Обновляем кнопки
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id.endswith(f"_{card_type}"):
                    item.disabled = True
                    item.style = discord.ButtonStyle.danger
                    item.label = f"✅ {item.label.split(' ', 1)[1]}"  # Убираем эмодзи и добавляем галочку
            
            # Отправляем уведомление в основной канал
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
                description=f"{interaction.user.display_name} раскрыл свою карту",
                color=3447003
            )
            embed.add_field(
                name=f"📋 {card_type_names.get(card_type, card_type.title())}",
                value=f"**{card.card_name}**",
                inline=False
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await announcements_channel.send(embed=embed)
            
            # Логируем раскрытие карты
            log = BunkerGameLog(
                game_id=self.game_id,
                round_number=game.current_round,
                actor_player_id=self.player_id,
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
                    await interaction.user.edit(nick=card.card_name)
                except discord.Forbidden:
                    pass
            
            await interaction.response.edit_message(
                content=f"✅ Карта '{card_type_names.get(card_type, card_type)}' раскрыта!",
                view=self
            )
    
    async def refresh_buttons(self):
        """Обновляет состояние кнопок на основе раскрытых карт"""
        async with get_async_session() as session:
            # Получаем все карты игрока
            cards = await session.execute(
                select(BunkerPlayerCard).where(BunkerPlayerCard.player_id == self.player_id)
            )
            cards = cards.scalars().all()
            
            revealed_cards = {card.card_type for card in cards if card.is_revealed}  # Убираем .lower()
            
            # Обновляем кнопки
            for item in self.children:
                if hasattr(item, 'custom_id'):
                    card_type = item.custom_id.split('_')[-1]
                    if card_type in revealed_cards:
                        item.disabled = True
                        item.style = discord.ButtonStyle.danger
                        # Убираем эмодзи и добавляем галочку
                        if not item.label.startswith("✅"):
                            item.label = f"✅ {item.label.split(' ', 1)[1]}"

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

class ActionCardView(discord.ui.View):
    """UI для использования карт действий"""
    
    def __init__(self, player_id: int, game_id: int, action_cards: List[str], bot):
        super().__init__(timeout=None)
        self.player_id = player_id
        self.game_id = game_id
        self.bot = bot
        
        # Создаем селект с картами действий игрока
        if action_cards:
            options = []
            for card_name in action_cards:
                card_info = ACTION_CARDS.get(card_name, {})
                description = card_info.get("description", "Неизвестный эффект")[:100]
                options.append(discord.SelectOption(
                    label=card_name,
                    description=description,
                    value=card_name
                ))
            
            card_select = discord.ui.Select(
                placeholder="Выберите карту действия для использования",
                options=options,
                custom_id=f"action_card_{game_id}_{player_id}"
            )
            
            async def card_select_callback(interaction: discord.Interaction):
                if interaction.user.id != await self.get_user_id():
                    await interaction.response.send_message("❌ Это не ваши карты!", ephemeral=True)
                    return
                
                card_name = interaction.data['values'][0] if interaction.data['values'] else None
                if not card_name:
                    await interaction.response.send_message("❌ Карта не выбрана!", ephemeral=True)
                    return
                
                await self.use_action_card(interaction, card_name)
            
            card_select.callback = card_select_callback
            self.add_item(card_select)
    
    async def get_user_id(self):
        """Получает user_id игрока"""
        async with get_async_session() as session:
            player = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.id == self.player_id)
            )
            player = player.scalar_one_or_none()
            return player.user_id if player else None
    
    async def use_action_card(self, interaction: discord.Interaction, card_name: str):
        """Обрабатывает использование карты действия"""
        await interaction.response.defer(ephemeral=True)
        
        async with get_async_session() as session:
            # Получаем игру и игрока
            game = await session.execute(
                select(BunkerGame).where(
                    and_(
                        BunkerGame.id == self.game_id,
                        BunkerGame.status == BunkerGameStatusENUM.RUNNING.value
                    )
                )
            )
            game = game.scalar_one_or_none()
            
            if not game:
                await interaction.followup.send("❌ Игра не активна!", ephemeral=True)
                return
            
            player = await session.execute(
                select(BunkerPlayer).where(BunkerPlayer.id == self.player_id)
            )
            player = player.scalar_one_or_none()
            
            if not player or player.is_expelled:
                await interaction.followup.send("❌ Вы не можете использовать карты!", ephemeral=True)
                return
            
            # Проверяем, что у игрока есть эта карта
            card = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == self.player_id,
                        BunkerPlayerCard.card_type == "action_card",
                        BunkerPlayerCard.card_name == card_name,
                        BunkerPlayerCard.is_revealed == False  # Неиспользованная карта
                    )
                )
            )
            card = card.scalar_one_or_none()
            
            if not card:
                await interaction.followup.send("❌ У вас нет этой карты или она уже использована!", ephemeral=True)
                return
            
            # Применяем эффект карты
            success = await self.apply_card_effect(card_name, game, player, session, interaction)
            
            if success:
                # Помечаем карту как использованную
                card.is_revealed = True
                await session.commit()
                
                # Удаляем кнопку использованной карты
                new_options = []
                for item in self.children:
                    if hasattr(item, 'options'):
                        for option in item.options:
                            if option.value != card_name:
                                new_options.append(option)
                
                # Обновляем селект
                if new_options:
                    self.clear_items()
                    new_select = discord.ui.Select(
                        placeholder="Выберите карту действия для использования",
                        options=new_options,
                        custom_id=f"action_card_{self.game_id}_{self.player_id}"
                    )
                    
                    async def new_callback(interaction: discord.Interaction):
                        card_name = interaction.data['values'][0] if interaction.data['values'] else None
                        await self.use_action_card(interaction, card_name)
                    
                    new_select.callback = new_callback
                    self.add_item(new_select)
                else:
                    # Все карты использованы
                    self.clear_items()
                    self.add_item(discord.ui.Button(
                        label="Все карты действий использованы",
                        disabled=True,
                        style=discord.ButtonStyle.secondary
                    ))
                
                await interaction.followup.send(f"✅ Карта '{card_name}' успешно использована!", ephemeral=True)
    
    async def apply_card_effect(self, card_name: str, game: BunkerGame, player: BunkerPlayer, session: AsyncSession, interaction: discord.Interaction):
        """Применяет эффект карты действия"""
        card_info = ACTION_CARDS.get(card_name, {})
        effect_type = card_info.get("effect_type")
        
        announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
        user = self.bot.get_user(player.user_id)
        
        try:
            if effect_type == "change_all_players":
                await self.effect_change_all_players(game, session, announcements_channel, user, card_name)
            elif effect_type == "swap_cards":
                await self.effect_swap_cards(game, session, announcements_channel, user, card_name, interaction)
            elif effect_type == "force_reveal":
                await self.effect_force_reveal(game, session, announcements_channel, user, card_name, interaction)
            elif effect_type == "immunity":
                await self.effect_immunity(game, player, session, announcements_channel, user, card_name, interaction)
            elif effect_type == "trigger_event":
                await self.effect_trigger_event(game, session, announcements_channel, user, card_name)
            elif effect_type == "increase_capacity":
                await self.effect_increase_capacity(game, session, announcements_channel, user, card_name)
            elif effect_type == "replace_all_cards":
                await self.effect_replace_all_cards(game, session, announcements_channel, user, card_name)
            elif effect_type == "heal_player":
                await self.effect_heal_player(game, session, announcements_channel, user, card_name, interaction)
            elif effect_type == "sicken_player":
                await self.effect_sicken_player(game, session, announcements_channel, user, card_name, interaction)
            elif effect_type == "peek_cards":
                await self.effect_peek_cards(game, session, user, card_name, interaction)
            else:
                await interaction.followup.send("❌ Неизвестный эффект карты!", ephemeral=True)
                return False
            
            # Логируем использование карты
            log = BunkerGameLog(
                game_id=game.id,
                round_number=game.current_round,
                actor_player_id=player.id,
                action_type=BunkerActionTypeENUM.ACTION_CARD_PLAYED.value,
                action_details={
                    "card_name": card_name,
                    "effect_type": effect_type
                }
            )
            session.add(log)
            await session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при применении эффекта карты {card_name}: {e}")
            await interaction.followup.send("❌ Произошла ошибка при использовании карты!", ephemeral=True)
            return False
    
    async def effect_change_all_players(self, game, session, channel, user, card_name):
        """Эффект: Смена реальности - меняет характеристику у всех игроков"""
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
        
        # Случайно выбираем тип карты для изменения
        card_types = ["profession", "skill", "baggage"]
        chosen_type = random.choice(card_types)
        
        type_names = {
            "profession": "профессии",
            "skill": "навыки", 
            "baggage": "багаж"
        }
        
        changed_players = []
        for player in players:
            # Находим карту этого типа у игрока
            card = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == player.id,
                        BunkerPlayerCard.card_type == chosen_type
                    )
                )
            )
            card = card.scalar_one_or_none()
            
            if card:
                # Генерируем новое значение
                if chosen_type == "profession":
                    new_value = random.choice(PROFESSIONS)
                elif chosen_type == "skill":
                    new_value = random.choice(SKILLS)
                elif chosen_type == "baggage":
                    new_value = random.choice(BAGGAGE)
                
                old_value = card.card_name
                card.card_name = new_value
                
                player_user = self.bot.get_user(player.user_id)
                if player_user:
                    changed_players.append(f"{player_user.display_name}: {old_value} → {new_value}")
        
        await session.commit()
        
        # Отправляем уведомление
        embeds = get_embeds("bunker/action_card_used",
            playerName=user.display_name,
            cardName=card_name,
            cardEffect=f"Все игроки получили новые {type_names[chosen_type]}",
            cardDetails="\n".join(changed_players) if changed_players else "Изменений не произошло"
        )
        await channel.send(embeds=embeds)
    
    async def effect_swap_cards(self, game, session, channel, user, card_name, interaction):
        """Эффект: Обмен картами между двумя игроками"""
        # Эта функция требует выбора игроков, пока упростим
        embeds = get_embeds("bunker/action_card_used",
            playerName=user.display_name,
            cardName=card_name,
            cardEffect="Запущен процесс обмена характеристиками",
            cardDetails="Функция будет доработана в следующем обновлении"
        )
        await channel.send(embeds=embeds)
    
    async def effect_force_reveal(self, game, session, channel, user, card_name, interaction):
        """Эффект: Принудительное раскрытие карты"""
        # Получаем случайного игрока со скрытыми картами
        players = await session.execute(
            select(BunkerPlayer).where(
                and_(
                    BunkerPlayer.game_id == game.id,
                    BunkerPlayer.is_expelled == False,
                    BunkerPlayer.id != await self.get_player_from_user_id(interaction.user.id)
                )
            )
        )
        players = players.scalars().all()
        
        target_player = random.choice(players) if players else None
        if not target_player:
            return
        
        # Находим скрытую карту
        hidden_cards = await session.execute(
            select(BunkerPlayerCard).where(
                and_(
                    BunkerPlayerCard.player_id == target_player.id,
                    BunkerPlayerCard.is_hidden == True,
                    BunkerPlayerCard.is_revealed == False
                )
            )
        )
        hidden_cards = hidden_cards.scalars().all()
        
        if hidden_cards:
            revealed_card = random.choice(hidden_cards)
            revealed_card.is_revealed = True
            
            target_user = self.bot.get_user(target_player.user_id)
            
            embeds = get_embeds("bunker/action_card_used",
                playerName=user.display_name,
                cardName=card_name,
                cardEffect=f"Раскрыта тайна игрока {target_user.display_name}",
                cardDetails=f"{revealed_card.card_type}: {revealed_card.card_name}"
            )
            await channel.send(embeds=embeds)
    
    async def effect_immunity(self, game, player, session, channel, user, card_name, interaction):
        """Эффект: Иммунитет от изгнания"""
        # Добавляем иммунитет в настройки игры
        settings = game.game_settings or {}
        immune_players = settings.get("immune_players", [])
        immune_players.append(player.id)
        settings["immune_players"] = immune_players
        game.game_settings = settings
        
        embeds = get_embeds("bunker/action_card_used",
            playerName=user.display_name,
            cardName=card_name,
            cardEffect=f"{user.display_name} получил иммунитет от изгнания",
            cardDetails="Действует до следующего голосования"
        )
        await channel.send(embeds=embeds)
    
    async def effect_trigger_event(self, game, session, channel, user, card_name):
        """Эффект: Вызвать событие в бункере"""
        event_name = random.choice(list(BUNKER_EVENTS.keys()))
        event_info = BUNKER_EVENTS[event_name]
        
        # Логируем событие
        log = BunkerGameLog(
            game_id=game.id,
            round_number=game.current_round,
            action_type=BunkerActionTypeENUM.EVENT_TRIGGERED.value,
            action_details={
                "event_name": event_name,
                "event_description": event_info["description"],
                "triggered_by_card": card_name
            }
        )
        session.add(log)
        
        embeds = get_embeds("bunker/event",
            eventName=event_name,
            eventDescription=event_info["description"],
            requiredProfessions=", ".join(event_info["required_professions"]),
            consequences=event_info["consequences"],
            triggeredBy=f"Карта действия '{card_name}' игрока {user.display_name}"
        )
        await channel.send(embeds=embeds)
    
    async def effect_increase_capacity(self, game, session, channel, user, card_name):
        """Эффект: Увеличить вместимость бункера"""
        game.bunker_capacity += 1
        
        embeds = get_embeds("bunker/action_card_used",
            playerName=user.display_name,
            cardName=card_name,
            cardEffect="Вместимость бункера увеличена на 1 место",
            cardDetails=f"Теперь в бункере может поместиться {game.bunker_capacity} человек"
        )
        await channel.send(embeds=embeds)
    
    async def effect_replace_all_cards(self, game, session, channel, user, card_name):
        """Эффект: Общая амнезия - заменить одну характеристику у всех"""
        # Аналогично change_all_players, но с заменой
        await self.effect_change_all_players(game, session, channel, user, "Общая амнезия")
    
    async def effect_heal_player(self, game, session, channel, user, card_name, interaction):
        """Эффект: Исцелить игрока"""
        # Пока упрощенная версия - лечим самого игрока
        player_card = await session.execute(
            select(BunkerPlayerCard).where(
                and_(
                    BunkerPlayerCard.player_id == self.player_id,
                    BunkerPlayerCard.card_type == "health"
                )
            )
        )
        player_card = player_card.scalar_one_or_none()
        
        if player_card:
            old_health = player_card.card_name
            player_card.card_name = "Отличное здоровье"
            
            embeds = get_embeds("bunker/action_card_used",
                playerName=user.display_name,
                cardName=card_name,
                cardEffect=f"Здоровье улучшено",
                cardDetails=f"{old_health} → Отличное здоровье"
            )
            await channel.send(embeds=embeds)
    
    async def effect_sicken_player(self, game, session, channel, user, card_name, interaction):
        """Эффект: Ухудшить здоровье игрока"""
        # Выбираем случайного игрока
        players = await session.execute(
            select(BunkerPlayer).where(
                and_(
                    BunkerPlayer.game_id == game.id,
                    BunkerPlayer.is_expelled == False
                )
            )
        )
        players = players.scalars().all()
        
        target_player = random.choice(players) if players else None
        if target_player:
            health_card = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == target_player.id,
                        BunkerPlayerCard.card_type == "health"
                    )
                )
            )
            health_card = health_card.scalar_one_or_none()
            
            if health_card:
                old_health = health_card.card_name
                health_card.card_name = "Хроническое заболевание"
                
                target_user = self.bot.get_user(target_player.user_id)
                
                embeds = get_embeds("bunker/action_card_used",
                    playerName=user.display_name,
                    cardName=card_name,
                    cardEffect=f"Здоровье игрока {target_user.display_name} ухудшено",
                    cardDetails=f"{old_health} → Хроническое заболевание"
                )
                await channel.send(embeds=embeds)
    
    async def effect_peek_cards(self, game, session, user, card_name, interaction):
        """Эффект: Подсмотреть карты игрока"""
        # Выбираем случайного игрока
        players = await session.execute(
            select(BunkerPlayer).where(
                and_(
                    BunkerPlayer.game_id == game.id,
                    BunkerPlayer.is_expelled == False,
                    BunkerPlayer.id != self.player_id
                )
            )
        )
        players = players.scalars().all()
        
        target_player = random.choice(players) if players else None
        if target_player:
            # Получаем все карты игрока
            cards = await session.execute(
                select(BunkerPlayerCard).where(BunkerPlayerCard.player_id == target_player.id)
            )
            cards = cards.scalars().all()
            
            target_user = self.bot.get_user(target_player.user_id)
            cards_info = []
            for card in cards:
                status = "Раскрыта" if card.is_revealed else "Скрыта"
                cards_info.append(f"{card.card_type}: {card.card_name} ({status})")
            
            # Отправляем информацию только игроку, использовавшему карту
            embed = discord.Embed(
                title=f"🔍 Карты игрока {target_user.display_name}",
                description="\n".join(cards_info),
                color=0x9932cc
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # В общий чат только уведомление
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            embeds = get_embeds("bunker/action_card_used",
                playerName=user.display_name,
                cardName=card_name,
                cardEffect=f"Подсмотрел карты игрока {target_user.display_name}",
                cardDetails="Информация отправлена в личные сообщения"
            )
            await announcements_channel.send(embeds=embeds)
    
    async def get_player_from_user_id(self, user_id: int):
        """Получает player_id по user_id"""
        async with get_async_session() as session:
            player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == self.game_id,
                        BunkerPlayer.user_id == user_id
                    )
                )
            )
            player = player.scalar_one_or_none()
            return player.id if player else None

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
        catastrophe="Тип катастрофы (по умолчанию случайная)",
        action_cards="Выдавать ли карты действий игрокам (по умолчанию True)",
        events="Включить ли случайные события в бункере (по умолчанию True)"
    )
    async def bunker_create(self, ctx: discord.ApplicationContext, 
                           capacity: Optional[int] = 10, 
                           catastrophe: Optional[str] = None,
                           action_cards: Optional[bool] = True,
                           events: Optional[bool] = True):
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
                    "allow_dynamic_events": events,
                    "action_cards_enabled": action_cards,
                    "secret_room_enabled": secret_room is not None,
                    "secret_room_opens_round": 3 if secret_room else None,
                    "catastrophe_description": catastrophe_info["description"],
                    "events_per_game": 2 if events else 0,
                    "event_min_round": 2,  # События начинаются с 2-го раунда
                    "immune_players": []  # Список игроков с иммунитетом
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
                
                # Генерируем карту действия если включено
                action_card = None
                if game.game_settings.get("action_cards_enabled", False):
                    action_card = generate_action_card()
                    cards["action_card"] = action_card
                
                # Сохраняем карты в БД
                for card_type, card_value in cards.items():
                    is_hidden = card_type in ["phobia", "additional_info", "health"]
                    card = BunkerPlayerCard(
                        player_id=player.id,
                        card_type=card_type,  # Используем строку
                        card_name=card_value,  # Используем простое поле
                        is_hidden=is_hidden
                    )
                    session.add(card)
                
                await session.commit()
                
                # Создаем View с кнопками для раскрытия карт
                card_reveal_view = CardRevealView(player.id, game.id, cards, self.bot)
                
                # Создаем View для карт действий если есть
                action_card_view = None
                if action_card:
                    action_card_view = ActionCardView(player.id, game.id, [action_card], self.bot)
                
                # Отправляем карты игроку в ЛС с кнопками
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
                    hiddenRole=cards["hidden_role"],
                    actionCard=action_card or "Нет"
                )
                try:
                    dm_message = await user.send(embeds=embeds, view=card_reveal_view)
                    # Сохраняем ID сообщения с кнопками
                    player.dm_cards_message_id = dm_message.id
                    
                    # Отправляем карты действий отдельным сообщением если есть
                    if action_card_view:
                        action_embed = discord.Embed(
                            title="🎴 Ваши карты действий",
                            description="Используйте эти карты в нужный момент для изменения хода игры!",
                            color=0x9932cc
                        )
                        action_embed.add_field(
                            name=f"🪄 {action_card}",
                            value=ACTION_CARDS[action_card]["description"],
                            inline=False
                        )
                        await user.send(embed=action_embed, view=action_card_view)
                        
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
                    hiddenRole="Скрыто",
                    actionCard="Есть карта действия" if action_card else "Нет карт действий"
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
            
            # Проверяем иммунитет игроков
            immune_players = game.game_settings.get("immune_players", [])
            non_immune_candidates = [pid for pid in expelled_candidates if pid not in immune_players]
            
            if len(expelled_candidates) > 1:
                if non_immune_candidates:
                    # Если есть кандидаты без иммунитета, изгоняем одного из них
                    expelled_candidates = non_immune_candidates
                    if len(expelled_candidates) > 1:
                        await ctx.followup.send(f"⚖️ Ничья в голосовании среди игроков без иммунитета! {len(expelled_candidates)} игроков получили по {max_votes} голосов. Требуется переголосование.", ephemeral=True)
                        return
                elif all(pid in immune_players for pid in expelled_candidates):
                    # Все кандидаты имеют иммунитет
                    await ctx.followup.send(f"🛡️ Все кандидаты на изгнание имеют иммунитет! Никто не изгнан.", ephemeral=True)
                    return
                else:
                    # Обычная ничья
                    await ctx.followup.send(f"⚖️ Ничья в голосовании! {len(expelled_candidates)} игроков получили по {max_votes} голосов. Требуется переголосование.", ephemeral=True)
                    return
            
            expelled_player_id = expelled_candidates[0]
            
            # Проверяем иммунитет изгоняемого игрока
            if expelled_player_id in immune_players:
                expelled_player = await session.execute(
                    select(BunkerPlayer).where(BunkerPlayer.id == expelled_player_id)
                )
                expelled_player = expelled_player.scalar_one_or_none()
                expelled_user = self.bot.get_user(expelled_player.user_id) if expelled_player else None
                
                await ctx.followup.send(f"🛡️ {expelled_user.display_name if expelled_user else 'Игрок'} имеет иммунитет от изгнания! Никто не изгнан.", ephemeral=True)
                
                # Убираем иммунитет (одноразовый)
                immune_players.remove(expelled_player_id)
                settings = game.game_settings.copy()
                settings["immune_players"] = immune_players
                game.game_settings = settings
                await session.commit()
                return
            
            # Изгоняем игрока
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

    @leader_group.command(name="trigger_event")
    async def bunker_trigger_event(self, ctx: discord.ApplicationContext):
        """Вызвать случайное событие в бункере"""
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
            
            # Генерируем событие
            event_info = generate_random_event()
            
            # Отправляем в основной канал
            announcements_channel = self.bot.get_channel(game.announcements_text_channel_id)
            
            embeds = get_embeds("bunker/event",
                eventName=event_info["name"],
                eventDescription=event_info["description"],
                eventSeverity=event_info["severity"].upper(),
                requiredProfessions=", ".join(event_info["required_professions"]),
                consequences=event_info["consequences"],
                triggeredBy="Ведущий игры"
            )
            await announcements_channel.send(embeds=embeds)
            
            # Логируем событие
            log = BunkerGameLog(
                game_id=game.id,
                round_number=game.current_round,
                action_type=BunkerActionTypeENUM.EVENT_TRIGGERED.value,
                action_details={
                    "event_name": event_info["name"],
                    "event_description": event_info["description"],
                    "severity": event_info["severity"],
                    "required_professions": event_info["required_professions"],
                    "consequences": event_info["consequences"],
                    "triggered_by": "leader"
                }
            )
            session.add(log)
            await session.commit()
            
            await ctx.followup.send(f"✅ Событие '{event_info['name']}' активировано!", ephemeral=True)

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
            
            # Сбрасываем иммунитеты после каждого раунда
            settings = game.game_settings or {}
            settings["immune_players"] = []
            game.game_settings = settings
            
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
            
            # Автоматическая генерация событий
            events_enabled = game.game_settings.get("allow_dynamic_events", False)
            min_event_round = game.game_settings.get("event_min_round", 2)
            events_per_game = game.game_settings.get("events_per_game", 2)
            
            # Считаем сколько событий уже было
            existing_events = await session.execute(
                select(BunkerGameLog).where(
                    and_(
                        BunkerGameLog.game_id == game.id,
                        BunkerGameLog.action_type == BunkerActionTypeENUM.EVENT_TRIGGERED.value
                    )
                )
            )
            existing_events_count = len(existing_events.scalars().all())
            
            # Генерируем событие с определенной вероятностью
            if (events_enabled and 
                game.current_round >= min_event_round and 
                existing_events_count < events_per_game and
                random.random() < 0.4):  # 40% шанс на событие каждый раунд
                
                event_info = generate_random_event()
                
                embeds = get_embeds("bunker/event",
                    eventName=event_info["name"],
                    eventDescription=event_info["description"],
                    eventSeverity=event_info["severity"].upper(),
                    requiredProfessions=", ".join(event_info["required_professions"]),
                    consequences=event_info["consequences"],
                    triggeredBy="Автоматическая система бункера"
                )
                await announcements_channel.send(embeds=embeds)
                
                # Логируем событие
                log = BunkerGameLog(
                    game_id=game.id,
                    round_number=game.current_round,
                    action_type=BunkerActionTypeENUM.EVENT_TRIGGERED.value,
                    action_details={
                        "event_name": event_info["name"],
                        "event_description": event_info["description"],
                        "severity": event_info["severity"],
                        "required_professions": event_info["required_professions"],
                        "consequences": event_info["consequences"],
                        "triggered_by": "automatic"
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
                        BunkerPlayerCard.card_type == card_type  # Используем строку напрямую
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

    @leader_group.command(name="test_card_buttons")
    async def bunker_test_card_buttons(self, ctx: discord.ApplicationContext):
        """Тестовая команда для отправки кнопок раскрытия карт"""
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
                await ctx.followup.send("❌ У вас нет прав для управления игрой или игра не активна!", ephemeral=True)
                return
            
            # Ищем игрока ведущего
            player = await session.execute(
                select(BunkerPlayer).where(
                    and_(
                        BunkerPlayer.game_id == game.id,
                        BunkerPlayer.user_id == ctx.author.id
                    )
                )
            )
            player = player.scalar_one_or_none()
            
            if not player:
                await ctx.followup.send("❌ Вы не участвуете в игре!", ephemeral=True)
                return
            
            # Получаем карты игрока
            cards = await session.execute(
                select(BunkerPlayerCard).where(BunkerPlayerCard.player_id == player.id)
            )
            cards = cards.scalars().all()
            
            if not cards:
                await ctx.followup.send("❌ У вас нет карт!", ephemeral=True)
                return
            
            # Собираем карты в словарь
            cards_dict = {card.card_type: card.card_name for card in cards}
            
            # Создаем View с кнопками
            card_reveal_view = CardRevealView(player.id, game.id, cards_dict, self.bot)
            
            # Обновляем состояние кнопок
            await card_reveal_view.refresh_buttons()
            
            # Отправляем тестовое сообщение
            embeds = get_embeds("bunker/player_cards_dm",
                playerName=ctx.author.display_name,
                professionName=cards_dict.get("profession", "Неизвестно"),
                healthStatus=cards_dict.get("health", "Неизвестно"),
                age=cards_dict.get("age", "Неизвестно"),
                gender=cards_dict.get("gender", "Неизвестно"),
                fullName=cards_dict.get("full_name", "Неизвестно"),
                skillName=cards_dict.get("skill", "Неизвестно"),
                itemName=cards_dict.get("baggage", "Неизвестно"),
                traitName=cards_dict.get("phobia", "Неизвестно"),
                extraInfo=cards_dict.get("additional_info", "Неизвестно"),
                hiddenRole=cards_dict.get("hidden_role", "Нет")
            )
            
            try:
                await ctx.author.send(content="🧪 **ТЕСТ:** Обновленное сообщение с кнопками раскрытия карт", embeds=embeds, view=card_reveal_view)
                await ctx.followup.send("✅ Тестовое сообщение с кнопками отправлено в ЛС!", ephemeral=True)
            except discord.Forbidden:
                await ctx.followup.send("❌ Не удалось отправить сообщение в ЛС!", ephemeral=True)

    @bunker_group.command(name="use_action")
    async def bunker_use_action(self, ctx: discord.ApplicationContext):
        """Использовать карту действия"""
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
            
            # Получаем неиспользованные карты действий игрока
            action_cards = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == player.id,
                        BunkerPlayerCard.card_type == "action_card",
                        BunkerPlayerCard.is_revealed == False  # Неиспользованные
                    )
                )
            )
            action_cards = action_cards.scalars().all()
            
            if not action_cards:
                await ctx.followup.send("❌ У вас нет доступных карт действий!", ephemeral=True)
                return
            
            # Создаем список названий карт
            card_names = [card.card_name for card in action_cards]
            
            # Создаем View для выбора карты
            action_view = ActionCardView(player.id, game.id, card_names, self.bot)
            
            embed = discord.Embed(
                title="🎴 Использование карт действий",
                description="Выберите карту действия для использования из выпадающего списка ниже:",
                color=0x9932cc
            )
            
            for card in action_cards:
                card_info = ACTION_CARDS.get(card.card_name, {})
                embed.add_field(
                    name=f"🪄 {card.card_name}",
                    value=card_info.get("description", "Описание недоступно"),
                    inline=False
                )
            
            embed.set_footer(text="После использования карта будет удалена из вашего инвентаря")
            
            await ctx.followup.send(embed=embed, view=action_view, ephemeral=True)

    @bunker_group.command(name="my_actions")
    async def bunker_my_actions(self, ctx: discord.ApplicationContext):
        """Показать ваши карты действий"""
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
                        BunkerPlayer.user_id == ctx.author.id
                    )
                )
            )
            player = player.scalar_one_or_none()
            
            if not player:
                await ctx.followup.send("❌ Вы не участвуете в игре!", ephemeral=True)
                return
            
            # Получаем все карты действий игрока
            action_cards = await session.execute(
                select(BunkerPlayerCard).where(
                    and_(
                        BunkerPlayerCard.player_id == player.id,
                        BunkerPlayerCard.card_type == "action_card"
                    )
                )
            )
            action_cards = action_cards.scalars().all()
            
            embed = discord.Embed(
                title="🎴 Ваши карты действий",
                color=0x9932cc
            )
            
            if not action_cards:
                embed.description = "У вас нет карт действий в этой игре."
            else:
                available_cards = []
                used_cards = []
                
                for card in action_cards:
                    card_info = ACTION_CARDS.get(card.card_name, {})
                    card_desc = card_info.get("description", "Описание недоступно")
                    
                    if card.is_revealed:  # Использованная карта
                        used_cards.append(f"~~{card.card_name}~~ - {card_desc}")
                    else:  # Доступная карта
                        available_cards.append(f"**{card.card_name}** - {card_desc}")
                
                if available_cards:
                    embed.add_field(
                        name="✅ Доступные карты",
                        value="\n".join(available_cards),
                        inline=False
                    )
                
                if used_cards:
                    embed.add_field(
                        name="❌ Использованные карты",
                        value="\n".join(used_cards),
                        inline=False
                    )
                
                embed.set_footer(text="Используйте /bunker use_action для активации карты")
            
            await ctx.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BunkerCog(bot)) 