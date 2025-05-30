import discord
import asyncio
import logging
import os
import random
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class BunkerAudioManager:
    """Управление звуковым сопровождением для игры Бункер"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients: Dict[int, discord.VoiceClient] = {}  # game_id -> voice_client
        self.audio_settings = {
            "enabled": True,
            "volume": 0.5,
            "sound_effects": True,
            "background_music": True,
            "voice_notifications": True
        }
        
        # Пути к аудиофайлам (относительно корня проекта)
        self.sounds = {
            # Атмосферная музыка
            "lobby_music": "sounds/bunker/lobby_ambient.mp3",
            "game_music": "sounds/bunker/bunker_ambient.mp3",
            "tension_music": "sounds/bunker/tension.mp3",
            "victory_music": "sounds/bunker/victory.mp3",
            "defeat_music": "sounds/bunker/defeat.mp3",
            
            # Звуки катастроф
            "nuclear_alarm": "sounds/bunker/nuclear_siren.mp3",
            "virus_alert": "sounds/bunker/biohazard.mp3",
            "earthquake": "sounds/bunker/earthquake.mp3",
            "explosion": "sounds/bunker/explosion.mp3",
            
            # Звуки событий
            "card_reveal": "sounds/bunker/card_flip.mp3",
            "voting_start": "sounds/bunker/voting_bell.mp3",
            "player_expelled": "sounds/bunker/expulsion.mp3",
            "event_triggered": "sounds/bunker/emergency.mp3",
            "secret_room": "sounds/bunker/door_open.mp3",
            
            # Уведомления
            "player_joined": "sounds/bunker/footsteps.mp3",
            "round_start": "sounds/bunker/countdown.mp3",
            "game_start": "sounds/bunker/bunker_close.mp3",
            
            # Голосовые уведомления
            "welcome": "sounds/bunker/voice/welcome.mp3",
            "catastrophe_announce": "sounds/bunker/voice/catastrophe.mp3",
            "voting_time": "sounds/bunker/voice/voting.mp3",
        }
    
    async def connect_to_voice(self, game_id: int, voice_channel) -> bool:
        """Подключается к голосовому каналу для игры"""
        try:
            if game_id in self.voice_clients:
                await self.disconnect_from_voice(game_id)
            
            voice_client = await voice_channel.connect()
            self.voice_clients[game_id] = voice_client
            logger.info(f"🎵 Подключен к голосовому каналу для игры {game_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к голосовому каналу: {e}")
            return False
    
    async def disconnect_from_voice(self, game_id: int):
        """Отключается от голосового канала"""
        if game_id in self.voice_clients:
            try:
                await self.voice_clients[game_id].disconnect()
                del self.voice_clients[game_id]
                logger.info(f"🔇 Отключен от голосового канала для игры {game_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка отключения от голосового канала: {e}")
    
    async def play_sound(self, game_id: int, sound_key: str, volume: Optional[float] = None, wait_finish: bool = False):
        """Воспроизводит звуковой эффект"""
        if not self.audio_settings["enabled"] or not self.audio_settings["sound_effects"]:
            return
            
        if game_id not in self.voice_clients:
            return
        
        voice_client = self.voice_clients[game_id]
        if not voice_client.is_connected():
            return
        
        sound_path = self.sounds.get(sound_key)
        if not sound_path:
            logger.warning(f"⚠️ Звук не найден в списке: {sound_key}")
            return
            
        if not os.path.exists(sound_path):
            logger.warning(f"⚠️ Звуковой файл не найден: {sound_path}")
            return
        
        try:
            # Останавливаем текущее воспроизведение если есть
            if voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.1)  # Небольшая пауза
            
            # Определяем громкость
            if volume is None:
                volume = self.audio_settings["volume"]
            
            # Создаем источник аудио
            source = discord.FFmpegPCMAudio(sound_path)
            
            # Применяем громкость
            if volume != 1.0:
                source = discord.PCMVolumeTransformer(source, volume=volume)
            
            # Воспроизводим
            voice_client.play(source, after=lambda e: logger.error(f'❌ Ошибка воспроизведения: {e}') if e else None)
            
            # Ожидаем окончания если нужно
            if wait_finish:
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                    
            logger.info(f"🔊 Воспроизведен звук: {sound_key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка воспроизведения звука {sound_key}: {e}")
    
    async def play_background_music(self, game_id: int, music_key: str, loop: bool = True):
        """Воспроизводит фоновую музыку"""
        if not self.audio_settings["background_music"]:
            return
        
        await self.play_sound(game_id, music_key, volume=0.2)  # Тише для фона
        
        # Зацикливание музыки
        if loop:
            asyncio.create_task(self._loop_background_music(game_id, music_key))
    
    async def _loop_background_music(self, game_id: int, music_key: str):
        """Зацикливает фоновую музыку"""
        while game_id in self.voice_clients:
            try:
                voice_client = self.voice_clients[game_id]
                
                # Проверяем, нужно ли продолжать воспроизведение
                if not voice_client.is_connected():
                    break
                    
                if not voice_client.is_playing():
                    await asyncio.sleep(2)  # Пауза между треками
                    await self.play_sound(game_id, music_key, volume=0.2)
                    
                await asyncio.sleep(5)  # Проверяем каждые 5 секунд
                
            except Exception as e:
                logger.error(f"❌ Ошибка в зацикливании музыки: {e}")
                break
    
    async def stop_all_audio(self, game_id: int):
        """Останавливает все аудио для игры"""
        if game_id in self.voice_clients:
            voice_client = self.voice_clients[game_id]
            if voice_client.is_playing():
                voice_client.stop()
                logger.info(f"⏹️ Остановлено аудио для игры {game_id}")
    
    async def set_volume(self, volume: float):
        """Устанавливает общую громкость (0.0 - 1.0)"""
        self.audio_settings["volume"] = max(0.0, min(1.0, volume))
        logger.info(f"🔊 Громкость установлена: {volume}")
    
    def toggle_audio(self, audio_type: str = "all"):
        """Переключает различные типы аудио"""
        if audio_type == "all":
            self.audio_settings["enabled"] = not self.audio_settings["enabled"]
        elif audio_type in self.audio_settings:
            self.audio_settings[audio_type] = not self.audio_settings[audio_type]
            
        logger.info(f"🔧 Переключен аудио тип '{audio_type}': {self.audio_settings.get(audio_type, self.audio_settings['enabled'])}")
    
    async def play_catastrophe_sound(self, game_id: int, catastrophe_type: str):
        """Воспроизводит звук катастрофы в зависимости от типа"""
        sound_map = {
            # Биологические угрозы
            "Летальный вирус": "voice/lethal-virus",
            "Зомби-вирус": "voice/zombie-virus",
            
            # Ядерные катастрофы
            "За день до ядерной войны": "voice/one-day-before-nuclear-war",
            "Ядерная зима": "voice/nuclear-winter",
            
            # Экологические катастрофы
            "Заражение мирового океана": "voice/ocean-contamination",
            "Климатическая катастрофа": "voice/climate-catastrophe",
            "Глобальное потепление": "voice/global-warming",
            
            # Космические угрозы
            "Атака инопланетного корабля": "voice/alien-attack",
            "Разрушение Луны": "voice/lunar-destroy",
            "Солнечный супер-шторм": "voice/solar-superstorm",
            
            # Технологические катастрофы
            "Неконтролируемые нанороботы": "voice/uncontrollable-nanorobots",
            "Цифровой захват разума": "voice/digital-mind-control",
            
            # Природные катастрофы
            "Великий нефтяной кризис": "voice/grand-oil-crisis",
            "Пробуждение вулканов": "voice/volcano-awakening",
            
            # Мистические катастрофы
            "Загадочные миражи": "voice/mysterious-mirages",
            "Колодец в преисподнюю": "voice/borehole-to-hell",
            
            # Планетарные катастрофы
            "Зачистка планеты от людей": "voice/planet-cleaning",
            "Нулевая полярность": "voice/zero-polarity"
        }
        
        sound_key = sound_map.get(catastrophe_type, "voice/catastrophe")  # Дефолтный звук, если тип не найден
        await self.play_sound(game_id, sound_key, volume=0.8, wait_finish=True)
        logger.info(f"🚨 Воспроизведен голос катастрофы: {catastrophe_type} -> {sound_key}")
    
    async def play_event_sound(self, game_id: int, event_name: str):
        """Воспроизводит звук события в бункере"""
        event_sounds = {
            "Проблемы с электричеством": "event_triggered",
            "Утечка радиации": "nuclear_alarm", 
            "Нехватка еды": "event_triggered",
            "Проблемы с водой": "event_triggered",
            "Психологический кризис": "event_triggered",
            "Пожар": "explosion",
            "Заболевание": "virus_alert",
            "Поломка систем связи": "event_triggered",
            "Нападение извне": "explosion",
            "Депрессия жителей": "event_triggered"
        }
        
        sound_key = event_sounds.get(event_name, "event_triggered")
        await self.play_sound(game_id, sound_key, volume=0.6)
        logger.info(f"⚠️ Воспроизведен звук события: {event_name} -> {sound_key}")
    
    def get_audio_status(self, game_id: int) -> dict:
        """Возвращает статус аудио для игры"""
        connected = game_id in self.voice_clients
        playing = connected and self.voice_clients[game_id].is_playing() if connected else False
        
        return {
            "connected": connected,
            "playing": playing,
            "settings": self.audio_settings.copy()
        }

# Глобальный экземпляр менеджера аудио
bunker_audio_manager = None 