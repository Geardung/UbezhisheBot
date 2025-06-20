# 🎵 Звуковая система игры "Бункер"

Эта папка содержит звуковые файлы для атмосферного сопровождения игры "Бункер".

## 📁 Структура папок

```
sounds/bunker/
├── README.md                 # Этот файл
├── lobby_ambient.mp3         # Фоновая музыка в лобби
├── bunker_ambient.mp3        # Атмосферная музыка во время игры
├── tension.mp3              # Напряженная музыка во время голосования
├── victory.mp3              # Музыка победы
├── defeat.mp3               # Музыка поражения
├── nuclear_siren.mp3        # Сирена ядерной тревоги
├── biohazard.mp3           # Сигнал биологической опасности
├── earthquake.mp3          # Звук землетрясения
├── explosion.mp3           # Звук взрыва
├── card_flip.mp3           # Звук переворачивания карты
├── voting_bell.mp3         # Звук начала голосования
├── expulsion.mp3           # Звук изгнания игрока
├── emergency.mp3           # Звук экстренной ситуации
├── door_open.mp3           # Звук открытия секретной комнаты
├── footsteps.mp3           # Шаги нового игрока
├── countdown.mp3           # Обратный отсчет
├── bunker_close.mp3        # Звук закрытия бункера
└── voice/                  # Голосовые уведомления
    ├── welcome.mp3         # "Добро пожаловать в бункер"
    ├── catastrophe.mp3     # Объявление катастрофы
    └── voting.mp3          # "Время голосования"
```

## 🎮 Использование в игре

### Фоновая музыка
- **Лобби**: `lobby_ambient.mp3` - спокойная атмосферная музыка
- **Игра**: `bunker_ambient.mp3` - тревожная музыка бункера
- **Голосование**: `tension.mp3` - напряженная музыка
- **Победа**: `victory.mp3` - триумфальная музыка
- **Поражение**: `defeat.mp3` - грустная музыка

### Звуки катастроф
- **Ядерные катастрофы**: `nuclear_siren.mp3`
- **Биологические угрозы**: `biohazard.mp3`
- **Природные катастрофы**: `earthquake.mp3`
- **Взрывы/разрушения**: `explosion.mp3`

### Игровые события
- **Раскрытие карты**: `card_flip.mp3`
- **Начало голосования**: `voting_bell.mp3`
- **Изгнание игрока**: `expulsion.mp3`
- **События в бункере**: `emergency.mp3`
- **Секретная комната**: `door_open.mp3`

### Уведомления
- **Присоединение игрока**: `footsteps.mp3`
- **Начало раунда**: `countdown.mp3`
- **Начало игры**: `bunker_close.mp3`

## 🔧 Технические требования

### Формат файлов
- **Поддерживаемые форматы**: MP3, WAV, OGG
- **Рекомендуемый формат**: MP3 (лучшее сжатие)
- **Битрейт**: 128-192 kbps
- **Частота дискретизации**: 44.1 kHz или 48 kHz

### Длительность
- **Фоновая музыка**: 2-5 минут (зацикливается)
- **Звуковые эффекты**: 1-10 секунд
- **Голосовые уведомления**: 2-5 секунд

### Громкость
- **Музыка**: -18 до -12 dB (тише речи)
- **Эффекты**: -12 до -6 dB (слышны, но не мешают)
- **Голос**: -6 до 0 dB (четко слышен)

## 🎨 Рекомендации по стилю

### Атмосфера
- **Постапокалиптическая тематика**
- **Напряженность и тревога**
- **Индустриальные звуки**
- **Эхо и реверберация**

### Избегать
- Слишком громких звуков
- Резких переходов
- Повторяющихся мелодий
- Слишком веселой музыки

## 📥 Получение звуков

### Бесплатные ресурсы
- [Freesound.org](https://freesound.org) - звуковые эффекты
- [Incompetech.com](https://incompetech.com) - музыка Kevin MacLeod
- [OpenGameArt.org](https://opengameart.org) - игровые звуки
- [BBC Sound Effects](http://bbcsfx.acropolis.org.uk) - профессиональные эффекты

### AI генерация
- **Mubert** - AI музыка
- **Soundraw** - AI композиции
- **AIVA** - AI оркестровые произведения

## ⚙️ Настройка

Звуковая система управляется через `BunkerAudioManager`:

```python
# Включение/выключение звука
audio_manager.toggle_audio("all")          # Все звуки
audio_manager.toggle_audio("sound_effects") # Только эффекты
audio_manager.toggle_audio("background_music") # Только музыка

# Настройка громкости
await audio_manager.set_volume(0.5)  # 50% громкости

# Воспроизведение
await audio_manager.play_sound(game_id, "card_reveal")
await audio_manager.play_background_music(game_id, "lobby_music")
```

## 🚀 Будущие улучшения

- [ ] Динамическая генерация музыки
- [ ] Персонализированные звуки для ролей
- [ ] 3D звук в Discord (стерео эффекты)
- [ ] Голосовая озвучка карт
- [ ] Интерактивные звуковые команды
- [ ] Запись и воспроизведение реакций игроков 