# Игра "Мафия" в Discord

## 1. Что такое "Мафия"?

"Мафия" — это салонная командная психологическая пошаговая ролевая игра с детективным сюжетом, моделирующая борьбу информированных друг о друге членов организованного меньшинства с неорганизованным большинством.

Жители города, обессилевшие от разгула мафии, выносят решение пересажать в тюрьму всех мафиози до единого. В ответ мафия объявляет войну до полного уничтожения всех порядочных горожан.

## 2. Основные правила

### Фазы игры:
*   **День:**
    *   Обсуждение между всеми выжившими игроками.
    *   Выдвижение кандидатур на "посадку" (исключение из игры).
    *   Общее голосование. Игрок, набравший большинство голосов, "покидает город" (выбывает из игры), раскрывая свою роль.
*   **Ночь:**
    *   "Город засыпает" (все игроки "закрывают глаза" / бот мутит всех в голосовом чате).
    *   "Просыпается мафия". Члены мафии знакомятся друг с другом (если это первая ночь и настроено соответствующим образом) и выбирают жертву для устранения.
    *   Другие активные роли (Доктор, Комиссар и т.д.) выполняют свои ночные действия.
*   **Голосование:** Происходит в конце "Дня" для выбора игрока, который будет "посажен".

### Условия победы:
*   **Мирные жители (и другие положительные роли):** Побеждают, если им удается устранить всех членов мафии.
*   **Мафия (и другие отрицательные роли):** Побеждает, если их количество становится равным или превышает количество мирных жителей, или когда устранение мирных становится невозможным другими способами.

### Стандартные роли:
*   **Мафия:** Группа игроков, знающих друг друга. Ночью они совместно выбирают, кого "убить".
*   **Мирный житель:** Большинство игроков. У них нет особых способностей, их задача — вычислить и "посадить" мафию днем.
*   **Доктор:** Каждую ночь может "вылечить" одного игрока, спасая его от убийства мафией. Не может лечить одного и того же игрока две ночи подряд (популярное правило). Себя лечить может, но часто это тоже ограничивают.
*   **Комиссар (Детектив):** Каждую ночь может проверить роль одного из игроков, чтобы узнать, является ли он мафией.

## 3. Реализация в Discord

Мини-игра "Мафия" в Discord с упором на взаимодействие внутри голосового чата.

### Голосовой чат:
*   Бот автоматически управляет мутами игроков:
    *   **Ночь:** Все игроки заглушаются, кроме ведущего. Мафия может быть перемещена в отдельный голосовой канал для обсуждения.
    *   **"Убитые" игроки:** Заглушаются в основном канале и перемещаются в специальный голосовой канал "Кладбище", где могут общаться только с другими "убитыми".
    *   Возможность для ведущего (если он есть) временно размутить/замутить игроков.
*   **Звуковое сопровождение:**
    *   Бот может воспроизводить короткие звуковые эффекты для ключевых событий:
        *   Наступление дня (например, крик петуха).
        *   Наступление ночи (например, вой волков, сверчки).
        *   Убийство (например, короткий драматический звук).
        *   Раскрытие роли.
        *   Окончание голосования.

### Архитектура каналов в создаваемой категории:

*   **Текстовые каналы:**
    *   `#общий-чат-мафии`: Для основной текстовой коммуникации, объявлений от бота (смена дня/ночи, итоги голосования и т.д.). Виден всем участникам игры.
    *   `#лог-игры`: Канал, куда бот будет записывать основные события игры (кто когда выбыл, действия ролей, если это предусмотрено настройками). Может быть доступен после игры или ведущему.
*   **Войс-каналы:**
    *   `🔊 Собрание`: Основной голосовой канал, где происходит обсуждение днем и объявляются результаты. Все живые игроки находятся здесь днем.
    *   `👻 Кладбище`: Голосовой канал для выбывших игроков. "Убитые" игроки автоматически перемещаются сюда и могут общаться только друг с другом. Канал виден и доступен только "умершим" игрокам и, возможно, ведущему.
    *   `🕵️ Дом Мафии`: Приватный голосовой канал для членов мафии. Ночью мафиози перемещаются сюда для обсуждения и выбора жертвы. Канал виден и доступен только членам мафии, а также призракам. Призраки могут заходить сюда, но без возможности разговаривать.
    *   `🏠 Дом игрока №1` (и так далее, по количеству игроков): Персональные голосовые "комнаты" для каждого игрока.
        *   **Ночью:** Каждый живой игрок (кроме мафии, которая в своем "Доме Мафии") может быть перемещен в свой личный "дом", чтобы "спать". Это помогает симулировать изоляцию ночью.
        *   Вход в "дом" ночью строго ограничен только "владельцем" дома.
        *   **Эстетическое переименование:**
            *   Если игрок — **Комиссар**, его дом может называться `⚖️ Тюрьма [Имя Игрока]`.
            *   Если игрок — **Доктор**, его дом может называться `🚑 Больница [Имя Игрока]`.
            *   Для остальных мирных жителей — `🏠 Дом [Имя Игрока]`.
        *   **Логирование в личных каналах (если решено использовать текстовые каналы для домов):** Если для каждого "дома" создается и текстовый канал, то в нем могут появляться специфические сообщения для игрока, например, результаты его ночных действий или попытка нападения на него, если он был спасен. Информация должна быть сформулирована так, чтобы не раскрывать лишнего (например, "Этой ночью кто-то пытался проникнуть в ваш дом, но вам удалось отбиться" вместо "Мафия пыталась вас убить, но Доктор вас спас").

### Команды бота:
*   `/mafia create`: Создает временную категорию с вышеописанной структурой каналов. Ведущий (создатель комнаты) может настраивать параметры игры.
*   `/mafia start`: Начинает игру после того, как все желающие присоединились. Бот случайным образом распределяет роли.
*   `/mafia role`: (Команда в ЛС боту) Игрок может напомнить свою роль личным сообщением от бота.
*   `/mafia vote [участник]`: Команда для голосования днем.
*   `/mafia action [участник/действие]`: (Команда в ЛС боту) Для ночных действий ролей (например, `/mafia kill [участник]` для мафии, `/mafia check [участник]` для комиссара, `/mafia heal [участник]` для доктора).
*   `/mafia players`: Показывает список живых игроков (без ролей).
*   `/mafia rules`: Показывает ссылку на правила или краткое описание.
*   `/mafia end`: (Для ведущего) Принудительно завершить игру.

### Система ролей:
*   **Базовые роли:** Мафия, Мирный житель, Доктор, Комиссар.
*   **Добавление своих ролей:**
    *   Реализовать систему, где администратор сервера (или специальная роль) может добавлять новые роли через конфигурационные файлы или команды бота.
    *   Для каждой новой роли нужно определить:
        *   Название роли.
        *   Команду (Мафия, Мирные).
        *   Описание способностей.
        *   Когда действует способность (ночь/день, постоянно).
        *   Ограничения на способность (например, раз за игру, не на себя).
        *   Приоритет действия (если несколько ролей действуют на одного игрока одновременно, например, Доктор и Маньяк).
    *   **Примеры кастомных ролей:**
        *   **Маньяк:** Играет сам за себя. Каждую ночь убивает одного игрока. Побеждает, если остается один.
        *   **Оборотень:** Изначально играет за мирных, но после первой ночи (или при определенных условиях) становится мафией.
        *   **Любовница:** Ночью выбирает одного игрока. Если этого игрока убивают, Любовница тоже умирает от горя.
        *   **Журналист:** Раз в игру может узнать точное количество мафиози в игре ночью.
*   **Настройка баланса:** Возможность для ведущего перед началом игры выбирать, какие роли будут участвовать и в каком количестве, для обеспечения интересного и сбалансированного игрового процесса.

### Игровой процесс:
*   **Ведение лога:** Бот ведет лог ключевых событий игры (смена фаз, кто кого пытался убить, кто был спасен, результаты голосований, кто выбыл). Этот лог может быть доступен после игры.
*   **Оповещения:**
    *   Смена дня и ночи.
    *   Начало и конец голосования.
    *   Результаты дневного голосования и ночных событий (кто был убит, кто спасен - без раскрытия имен активных ролей, например, "Этой ночью мафия пыталась совершить убийство, но Доктор был начеку!").
    *   Победившая команда в конце игры.
*   **Интерфейс:** Использование эмбедов Discord для красивого отображения информации (роли, голосования, итоги).

## 4. Дополнительные идеи для интересного решения

*   **Система репутации/опыта:** За успешные действия (например, комиссар нашел мафию, доктор спас мирного) игроки могут получать очки.
*   **Достижения:** За выполнение определенных условий в игре (например, "Выжить, будучи единственным мирным против трех мафиози").
*   **Сценарии:** Предустановленные наборы ролей и правил для разных типов игр (классика, безумие с кучей активных ролей и т.д.).
*   **Ведущий:** Возможность назначить игрока или бота на роль ведущего, который будет комментировать происходящее и помогать с организацией. Если ведущий - игрок, он не участвует в игре как активная роль. Бот-ведущий может использовать звуковое сопровождение.
*   **"Последнее слово":** Убитый или "посаженный" игрок может иметь право на последнее слово перед окончательным выбыванием.
*   **Таймеры:** Настраиваемые таймеры для обсуждения днем и для ночных ходов.

## 5. Предлагаемая структура базы данных

Для хранения информации об играх, игроках, их ролях и действиях, предлагается следующая структура таблиц:

### Таблица `MafiaGames` (Игры)
*   `game_id` (INT, Primary Key, Auto Increment): Уникальный идентификатор игры.
*   `guild_id` (BIGINT): ID сервера (гильдии) Discord, где проходит игра.
*   `category_channel_id` (BIGINT): ID созданной категории каналов для игры.
*   `main_voice_channel_id` (BIGINT): ID основного голосового канала ("Собрание").
*   `main_text_channel_id` (BIGINT): ID основного текстового канала ("#общий-чат-мафии").
*   `mafia_voice_channel_id` (BIGINT, NULLABLE): ID голосового канала мафии ("Дом Мафии").
*   `cemetery_voice_channel_id` (BIGINT, NULLABLE): ID голосового канала "Кладбище".
*   `log_text_channel_id` (BIGINT, NULLABLE): ID текстового канала для логов ("#лог-игры").
*   `leader_id` (BIGINT): ID пользователя Discord, запустившего игру (ведущий).
*   `status` (VARCHAR(20)): Статус игры (например, "lobby", "running", "finished", "cancelled").
*   `start_time` (TIMESTAMP, NULLABLE): Время начала игры.
*   `end_time` (TIMESTAMP, NULLABLE): Время окончания игры.
*   `winner_team` (VARCHAR(50), NULLABLE): Команда-победитель (например, "Мирные", "Мафия", "Маньяк").
*   `game_settings` (JSON, NULLABLE): Настройки игры (например, список активных ролей, таймеры и т.д.).

### Таблица `MafiaPlayers` (Игроки в конкретной игре)
*   `player_id` (INT, Primary Key, Auto Increment): Уникальный идентификатор записи игрока в игре.
*   `game_id` (INT, Foreign Key -> `MafiaGames.game_id`): ID игры, к которой привязан игрок.
*   `user_id` (BIGINT, Foreign Key -> `User.id` из вашей основной таблицы пользователей): ID пользователя Discord.
*   `role_id` (INT, Foreign Key -> `MafiaRoles.role_id`, NULLABLE): ID назначенной роли.
*   `is_alive` (BOOLEAN, Default: TRUE): Статус игрока (жив/мертв).
*   `death_night_number` (INT, NULLABLE): Номер ночи, в которую игрок умер (если применимо).
*   `death_reason` (VARCHAR(255), NULLABLE): Причина смерти (например, "убит мафией", "повешен днем").
*   `personal_voice_channel_id` (BIGINT, NULLABLE): ID личного голосового "дома" игрока.
*   `join_time` (TIMESTAMP, Default: CURRENT_TIMESTAMP): Время присоединения игрока к лобби/игре.
*   `leave_time` (TIMESTAMP, NULLABLE): Время выхода игрока из игры (если покинул досрочно).

### Таблица `MafiaRoles` (Роли в Мафии)
*   `role_id` (INT, Primary Key, Auto Increment): Уникальный идентификатор роли.
*   `role_name` (VARCHAR(100), Unique): Название роли (например, "Мафия", "Доктор", "Комиссар").
*   `role_description` (TEXT, NULLABLE): Описание способностей роли.
*   `team` (VARCHAR(50)): Команда (например, "Мафия", "Мирные", "Нейтралы").
*   `is_custom_role` (BOOLEAN, Default: FALSE): Является ли роль пользовательской.
*   `abilities` (JSON, NULLABLE): Описание способностей в формате JSON для программной обработки (например, может ли блокировать, проверять, лечить, убивать; количество применений и т.д.).

### Таблица `MafiaGameLogs` (Логи действий в игре)
*   `log_id` (INT, Primary Key, Auto Increment): Уникальный идентификатор записи лога.
*   `game_id` (INT, Foreign Key -> `MafiaGames.game_id`): ID игры.
*   `round_number` (INT, NULLABLE): Номер игрового раунда (день/ночь).
*   `phase` (VARCHAR(10), NULLABLE): Фаза игры ("день" или "ночь").
*   `actor_player_id` (INT, Foreign Key -> `MafiaPlayers.player_id`, NULLABLE): ID игрока-инициатора действия.
*   `target_player_id` (INT, Foreign Key -> `MafiaPlayers.player_id`, NULLABLE): ID игрока-цели действия.
*   `action_type` (VARCHAR(50)): Тип действия (например, "VOTE", "KILL_ATTEMPT", "HEAL", "CHECK_ROLE", "CHAT_MESSAGE", "GAME_START", "PLAYER_DEATH", "GAME_END").
*   `action_details` (JSON, NULLABLE): Дополнительные детали действия (например, за кого проголосовал, результат проверки роли).
*   `timestamp` (TIMESTAMP, Default: CURRENT_TIMESTAMP): Время события.

### Таблица `MafiaRoleSettings` (Настройки ролей для конкретной игры) - Опционально
*Если нужно будет хранить, какие именно роли и в каком количестве были выбраны для *конкретной* игры, а не только общие настройки игры в `MafiaGames.game_settings`.*
*   `game_role_setting_id` (INT, Primary Key, Auto Increment)
*   `game_id` (INT, Foreign Key -> `MafiaGames.game_id`)
*   `role_id` (INT, Foreign Key -> `MafiaRoles.role_id`)
*   `count` (INT): Количество игроков с этой ролью в данной игре.

Эта структура должна покрыть основные потребности для игры "Мафия". Конечно, её можно будет дополнять и изменять по мере необходимости в процессе разработки!

Это основа для технической документации. Её можно будет дополнять и изменять по мере разработки. 

## 6. Структура и типы эмбедов

Для улучшения визуального восприятия и информативности, игра "Мафия" будет использовать эмбеды Discord для различных уведомлений и сообщений. Эмбеды будут храниться в виде JSON-шаблонов в директории `embeds/mafia/`.

### Основные типы эмбедов:

1.  **`role_assignment.json`** (Личное сообщение игроку)
    *   **Назначение:** Отправляется при старте игры для информирования игрока о его роли, а также по команде `/mafia role` для напоминания.
    *   **Содержимое:**
        *   Приветствие игрока.
        *   Название его роли.
        *   Принадлежность к команде (Мирные, Мафия и т.д.).
        *   Подробное описание роли и её способностей.
        *   Возможна иконка роли и цвет, соответствующий команде.
    *   **Пример полей в JSON:** `%playerName%`, `%roleName%`, `%teamName%`, `%roleDescription%`, `%roleAbilities%`, `%roleColor%`, `%roleIconUrl%`.

2.  **`night_starts.json`** (Общий игровой чат)
    *   **Назначение:** Уведомление о начале ночной фазы.
    *   **Содержимое:**
        *   Атмосферный заголовок и описание наступления ночи.
        *   Тематическое изображение (например, луна, тёмный лес).
        *   Тёмная цветовая схема.
    *   **Пример полей в JSON:** `%nightImageUrl%`.

3.  **`day_starts.json`** (Общий игровой чат)
    *   **Назначение:** Уведомление о начале дневной фазы.
    *   **Содержимое:**
        *   Заголовок и описание наступления дня.
        *   Информация об итогах ночи (кто был убит, если это публичная информация).
        *   Тематическое изображение (например, солнце, рассвет).
        *   Светлая цветовая схема.
    *   **Пример полей в JSON:** `%nightResults%`, `%dayImageUrl%`.

4.  **`voting_starts.json`** (Общий игровой чат)
    *   **Назначение:** Объявление о начале периода голосования.
    *   **Содержимое:**
        *   Призыв к голосованию.
        *   Напоминание команды для голосования (`/mafia vote @пользователь`).

5.  **`player_eliminated.json`** (Общий игровой чат)
    *   **Назначение:** Сообщение о выбывшем игроке (в результате голосования или ночных действий).
    *   **Содержимое:**
        *   Информация о том, кто покинул игру.
        *   Раскрытие роли выбывшего игрока и его команды.

6.  **`game_result.json`** (Общий игровой чат)
    *   **Назначение:** Объявление итогов игры.
    *   **Содержимое:**
        *   Информация о победившей команде.
        *   Список выживших игроков (опционально с их ролями).

7.  **`action_specific_embeds.json`** (Личные сообщения или общий чат, в зависимости от действия)
    *   **Назначение:** Эмбеды для специфичных действий ролей.
        *   Например, сообщение комиссару о результате его проверки.
        *   Сообщение доктору о результате его лечения (спас или нет).
        *   Сообщение мафии о выборе жертвы или результате их атаки.
    *   **Содержимое:** Будет варьироваться в зависимости от роли и действия. Главное – предоставить необходимую информацию без раскрытия лишнего другим игрокам.

### Организация файлов:

*   Каждый тип эмбеда будет представлен отдельным JSON-файлом в папке `embeds/mafia/` (например, `role_assignment.json`, `night_starts.json`).
*   В JSON-шаблонах будут использоваться переменные-плейсхолдеры (например, `%playerName%`), которые бот будет заменять на актуальные данные перед отправкой сообщения.

Эта система позволит гибко настраивать внешний вид сообщений и легко добавлять новые типы уведомлений по мере необходимости. 