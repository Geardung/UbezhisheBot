from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy import String, Table, Column, MetaData, ForeignKey, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import BigInteger, Text, CHAR, Boolean, Integer, Float, ARRAY, JSON

class VoiceLogTypeENUM(Enum): # ENUM для состояний ;)
    
    enter = "enter" # Вошёл
    exit = "exit" # Вышел

class PrivateActionTypeENUM(Enum):
    
    invite = "invite" # Пригласили кого-та
    kick = "kick" # Кикнули кого-та
    
    change = "change" # Изменение настроек

class Base(DeclarativeBase):
    pass

class User(Base):
    
    __tablename__ = "user"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # User ID пользователя с Дискорда
    
    tokens: Mapped[int] = mapped_column(Integer, default=0) # Баланс пользователя для внутренних услуг
    
    birthday: Mapped[int] = mapped_column(Integer, nullable=True) # День рождения пользователя. Мы одна большая семья, поэтому без этого параметра нельзя пройти

    time_spended_summary: Mapped[int] = mapped_column(Integer, nullable=True, default=0) # Сколько проведено времени
    
class TimeCounterLog(Base):

    __tablename__ = "time_counter_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE")) # Юзер, который вошёл\вышел в войс
    
    log_type: Mapped[VoiceLogTypeENUM] # Что сделал?
    
    channel_id: Mapped[int] = mapped_column(BigInteger) # Куда именно, войс айди
    
    parse_id: Mapped[int] = mapped_column(ForeignKey("time_parse.id"), nullable=True) # Юзер, который вошёл\вышел в войс
    
    timestamp: Mapped[int] = mapped_column(BigInteger, default=int(datetime.now().timestamp()))

class TimeParse(Base):
    
    __tablename__ = "time_parse"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    
    timestamp_start: Mapped[int] = mapped_column(BigInteger, default=int(datetime.now().timestamp())) # Парс начат

class PrivateRoom(Base):
    
    __tablename__ = "private_room"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # ID роли 
    
    timestamp_create: Mapped[int] = mapped_column(BigInteger, default=int(datetime.now().timestamp()))
    
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))

    label: Mapped[str] = mapped_column(nullable=True)
    color: Mapped[str] = mapped_column(nullable=True)
    icon:  Mapped[str] = mapped_column(nullable=True)

class PrivateRoomLog(Base):
    
    __tablename__ = "private_room_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    
    room_id: Mapped[int] = mapped_column(ForeignKey("private_room.id", ondelete="CASCADE"))
    
    action_type: Mapped[PrivateActionTypeENUM] # Что произошло
    
    actor: Mapped[int] = mapped_column(BigInteger) # Кто инициатор
    
    object: Mapped[int] = mapped_column(BigInteger)
    
    before: Mapped[str] = mapped_column(String, nullable=True)
    after:  Mapped[str] = mapped_column(String, nullable=True)

class PrivateRoomMember(Base):
    
    __tablename__ = "private_room_member"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True) 
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE")) # ID пользователя
    
    room_id: Mapped[int] = mapped_column(ForeignKey("private_room.id", ondelete="CASCADE")) # Комната
    
    permissions: Mapped[str] = mapped_column(String, nullable=True) # Права?
    
    log_id: Mapped[int] = mapped_column(ForeignKey("private_room_log.id", ondelete="CASCADE")) # Лог того, как был добавлен
    
    

metadata = Base.metadata

class MafiaGameStatusENUM(Enum):
    LOBBY = "lobby"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"

class MafiaTeamENUM(Enum):
    MAFIA = "mafia"
    TOWN = "town"
    NEUTRAL = "neutral"

class MafiaActionTypeENUM(Enum):
    VOTE = "vote"
    KILL_ATTEMPT = "kill_attempt"
    HEAL = "heal"
    CHECK_ROLE = "check_role"
    CHAT_MESSAGE = "chat_message"
    GAME_START = "game_start"
    PLAYER_DEATH = "player_death"
    GAME_END = "game_end"

class MafiaGame(Base):
    __tablename__ = "mafia_game"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    category_channel_id: Mapped[int] = mapped_column(BigInteger)
    main_voice_channel_id: Mapped[int] = mapped_column(BigInteger)
    main_text_channel_id: Mapped[int] = mapped_column(BigInteger)
    mafia_voice_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    cemetery_voice_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    log_text_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    status: Mapped[MafiaGameStatusENUM] = mapped_column(String(20))
    start_time: Mapped[int] = mapped_column(BigInteger, nullable=True)
    end_time: Mapped[int] = mapped_column(BigInteger, nullable=True)
    winner_team: Mapped[str] = mapped_column(String(50), nullable=True)
    game_settings: Mapped[str] = mapped_column(JSON, nullable=True)
    current_round: Mapped[int] = mapped_column(Integer, default=1)
    lobby_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)  # ID сообщения с эмбедом лобби

class MafiaPlayer(Base):
    __tablename__ = "mafia_player"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("mafia_game.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("mafia_role.id"), nullable=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    death_night_number: Mapped[int] = mapped_column(Integer, nullable=True)
    death_reason: Mapped[str] = mapped_column(String(255), nullable=True)
    personal_voice_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    join_time: Mapped[int] = mapped_column(BigInteger, default=lambda: int(datetime.now().timestamp()))
    leave_time: Mapped[int] = mapped_column(BigInteger, nullable=True)

class MafiaRole(Base):
    __tablename__ = "mafia_role"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_name: Mapped[str] = mapped_column(String(100), unique=True)
    role_description: Mapped[str] = mapped_column(Text, nullable=True)
    team: Mapped[MafiaTeamENUM] = mapped_column(String(50))
    is_custom_role: Mapped[bool] = mapped_column(Boolean, default=False)
    abilities: Mapped[str] = mapped_column(JSON, nullable=True)

class MafiaGameLog(Base):
    __tablename__ = "mafia_game_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("mafia_game.id", ondelete="CASCADE"))
    round_number: Mapped[int] = mapped_column(Integer, nullable=True)
    phase: Mapped[str] = mapped_column(String(10), nullable=True)
    actor_player_id: Mapped[int] = mapped_column(ForeignKey("mafia_player.id"), nullable=True)
    target_player_id: Mapped[int] = mapped_column(ForeignKey("mafia_player.id"), nullable=True)
    action_type: Mapped[MafiaActionTypeENUM] = mapped_column(String(50))
    action_details: Mapped[str] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[int] = mapped_column(BigInteger, default=lambda: int(datetime.now().timestamp()))

class MafiaRoleSetting(Base):
    __tablename__ = "mafia_role_setting"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("mafia_game.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("mafia_role.id", ondelete="CASCADE"))
    count: Mapped[int] = mapped_column(Integer)
