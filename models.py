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
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    
    timestamp_create: Mapped[int] = mapped_column(BigInteger, default=int(datetime.now().timestamp()))
    
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(BigInteger)
    
    label: Mapped[str]
    color: Mapped[str]
    icon:  Mapped[str]

class PrivateRoomLog(Base):
    
    __tablename__ = "private_room_log"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    
    room_id: Mapped[int] = mapped_column(ForeignKey("private_room.id", ondelete="CASCADE"))
    
    action_type: Mapped[PrivateActionTypeENUM]
    
    object: Mapped[int] = mapped_column(BigInteger)
    
    before: Mapped[str] = mapped_column(String, nullable=True)
    after:  Mapped[str] = mapped_column(String, nullable=True)

class PrivateRoomMember(Base):
    
    __tablename__ = "private_room_member"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE")) # ID пользователя
    
    room_id: Mapped[int] = mapped_column(ForeignKey("private_room.id", ondelete="CASCADE")) # Комната
    
    permissions: Mapped[str] = mapped_column(String, nullable=True) # Права?
    
    log_id: Mapped[int] = mapped_column(ForeignKey("private_room_log.id", ondelete="CASCADE")) # Лог того, как был добавлен
    
    

metadata = Base.metadata
