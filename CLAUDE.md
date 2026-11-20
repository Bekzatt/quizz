# Білім жарысы

Образовательная игра-раннер для уроков информатики (для учеников, интерфейс на **казахском**). Ученик бежит, перепрыгивает вирусы 👾, собирает теңге ₸ и отвечает на вопросы по информатике у ворот ❓. Очки: правильный ответ +10 (плюс бонус за серию), вирус −3, теңге +1.

**Статус: версия завершена (2026-11-20).** Обе версии работают и проверены. Новые изменения вносить только по запросу пользователя.

## Структура

```
quizz/
├─ quizzWifi/                # Версия 1 (Wi-Fi)
│  ├─ bilim-jarysy.html        # игра + экран учителя + вход с телефона, один файл
│  ├─ server.py                # сервер на stdlib Python (без зависимостей), ищет html рядом с собой
│  └─ start.bat                # запуск для учителя (двойной клик)
└─ quizzOnline/              # Версия 2 (онлайн, Firebase)
   ├─ public/index.html      # игра (выросла из quizzWifi/bilim-jarysy.html, сеть заменена на Firebase)
   ├─ database.rules.json    # правила безопасности Realtime Database
   ├─ firebase.json          # хостинг сайта bilim-jarysy (rewrite ** → index.html, Cache-Control: no-cache) + эмуляторы
   ├─ .firebaserc            # проект: informatika-jarysy
   └─ README.md              # инструкция для учителя (на русском)
```

## Режимы игры (в обеих версиях)
- **Бір құрылғыда** — 1–4 игрока на одном экране, у каждого своя дорожка. Клавиши: Q W E / Z X C / I O P / ← ↓ →. Первая клавиша при беге = прыжок, при вопросе = вариант ответа 1/2/3. На тач-устройствах кнопка «⬆ Секіру» в каждой дорожке.
- **Сетевой** — каждый ученик на своём телефоне, учитель видит лобби → живой рейтинг → пьедестал.

## Версия 1 — Wi-Fi (`quizzWifi/`)
- Запуск: `start.bat` → `python server.py --open` → открывает `http://localhost:8000/host`. Ученики: `http://<IP компьютера>:8000` (QR на экране учителя).
- `start.bat` должен оставаться **только ASCII и с CRLF** (с LF/кириллицей cmd ломал команды и показывал «Безопасность Windows»).
- Сервер: `ThreadingHTTPServer`, состояние в памяти `S` под `lock`, клиенты опрашивают сервер (`/api/update` раз в 0,5–1 с). `allow_reuse_address=False` + `SO_EXCLUSIVEADDRUSE`, иначе на Windows второй сервер садился на тот же порт.
- API: `GET /api/state|/api/game|/api/info`; `POST /api/join|/api/update|/api/leave` (ученики); `POST /api/start|/api/stop|/api/reset|/api/kick|/api/unban` — **только с 127.0.0.1** (компьютер учителя).
- Кик: id попадает в `S["kicked"]` → `/api/update` отвечает **410** (клиент показывает «шығарды» и НЕ переподключается сам; 404 = сервер перезапущен → авто-rejoin). Бан: по **IP** ученика (`S["banned"]`), т.к. новый id можно получить в любой момент; сбрасывается при перезапуске сервера.
- Порт меняется переменной `PORT`. Для тестов использовать `PORT=8010`, чтобы не задеть сервер пользователя на 8000.

## Версия 2 — онлайн (`quizzOnline/`)
- Сайт: **https://bilim-jarysy.web.app** (учитель: `/?host`, ученик: `/?room=1234`). Старый сайт `informatika-jarysy` (web.app и firebaseapp.com) **выключен** по просьбе пользователя (`firebase hosting:disable --site informatika-jarysy`), отдаёт 404; удалить его нельзя — это сайт по умолчанию проекта. Проект Firebase `informatika-jarysy` (ID проекта менять нельзя), Realtime Database (europe-west1), Anonymous Auth, тариф Spark (лимит 100 одновременных подключений).
- Название игры в интерфейсе — **«Білім жарысы»** (было «Информатика жарысы»). Файл Wi-Fi-версии переименован в `bilim-jarysy.html` (`server.py` → `GAME_FILE`).
- Деплой (из `quizzOnline/`): `firebase deploy` (правила + хостинг) или `firebase deploy --only hosting` — `firebase.json` деплоит только сайт `bilim-jarysy` (не добавлять обратно `informatika-jarysy` — деплой снова включит старый адрес). Установлен `firebase-tools@13.35.1` глобально (v14+ требует Java 21, на ПК Java 11). Пользователь уже залогинен.
- Firebase SDK 10.12.2 грузится динамическим `import()` с gstatic; конфиг берётся из `/__/firebase/init.json` (работает только на Firebase Hosting / эмуляторе).
- Данные: `rooms/{4 цифры}/meta` (hostUid, phase lobby|play|end|closed, gameId, seed, dur, startAt, questions, created, **hostOnline, active, locked**), `rooms/{code}/players/{uid}`, `rooms/{code}/banned/{uid}`, `roomIndex/{code}` (список комнат для очистки, без личных данных). Время — `.info/serverTimeOffset`; присутствие учеников — `onDisconnect` → `online:false`.
- Брошенные комнаты: экран учителя ставит `hostOnline:true` + `active` (heartbeat раз в 5 мин), `onDisconnect` → `hostOnline:false`. Комната **брошена**, если `hostOnline!==true` и `active` старше 2 ч (или без `active` и `created` старше 12 ч). Cloud Functions недоступны на Spark, поэтому очищает клиент: `cleanupStaleRooms()` при каждом открытии экрана учителя проходит `roomIndex` (до 25 комнат) и удаляет брошенные; правила разрешают это любому только для брошенных. Кнопка «✕ Бөлмені жабу» удаляет комнату сразу (сначала `phase:'closed'`, чтобы ученики увидели «Мұғалім бөлмені жапты»).
- Замок комнаты: `meta.locked` (boolean), кнопка `#hLock` под кодом. Правило `players/$uid`: ученик может **создать** свой узел только если `locked !== true` (`data.exists() ||` …), обновлять существующий — всегда. Это закрывает обход бана через инкогнито (бан по uid). `createRoom` пишет meta без `locked` → новая комната открыта. Правила генерировались скриптом (в scratchpad, не сохранён) — правь `database.rules.json` напрямую.
- Правила: только создатель комнаты (`hostUid`) меняет `meta`, кикает и банит; ученик пишет только свой узел и только если не забанен; поля валидируются (имя ≤20, `av` без `<>&"`, цвет `#RRGGBB`, очки 0–5000, лишние поля запрещены); брошенные комнаты (см. выше) можно удалять и переиспользовать любому (`created` = серверный `now`).
- Учитель — это анонимный uid браузера: в другом браузере/на другом origin будет другой пользователь. Для тестов «учитель + ученик» в одном браузере: на эмуляторе `localhost:5000` и `127.0.0.1:5000` (старый трюк с `firebaseapp.com` больше не работает — сайт выключен).
- В `database.rules.json` условие «комната брошена» повторяется в `meta`, `players`, `banned`, `roomIndex` — при изменении порогов (2 ч / 12 ч) правь все четыре места и `STALE_MS`/`OLD_MS` в `index.html`.

## Общий игровой код
`quizzOnline/public/index.html` скопирован из `quizzWifi/bilim-jarysy.html` и отличается **только сетевой частью** (раздел `// ================= ОНЛАЙН (Firebase)` vs `// ================= ЖЕЛІ (Wi-Fi режимі)`, экран учителя, поле кода комнаты). Игровой движок, стили, вопросы, форма вопросов одинаковые — **при изменении игры правь оба файла**.
- Вопросы: `BASE_Q` в начале скрипта, формат строки `Сұрақ | Дұрыс | Қате | Қате` (разделитель `|` или табуляция). Свои вопросы учителя хранятся в `localStorage['ij_q']` и редактируются формой `mountQEditor`.
- Размеры: `PLAYER_SCALE`, `COIN_R`; физика: `SPEED, GRAV, JUMP, PW, PH, BOOST`. Трасса детерминирована сидом (`makeCourse`), у всех игроков одна.
- Стиль: iOS (системные цвета `--blue #007AFF` и т.д., сегменты, «пилюли», стекло). Тексты интерфейса — казахский.
- **Безопасность:** всё, что пришло от учеников (name, av, color, числа), выводить только через `esc()` / `safeColor()` / `cleanPlayers()`. В Firebase-версии без этого была подтверждённая XSS на экране учителя.

## Тестирование
- Логику игры гонять синхронно из JS: `cancelAnimationFrame(raf)` и вызывать `loop(t)` с шагом 16 мс (в скрытой панели браузера rAF не тикает). Бот прыгает, если ближайший блок `< 12u`.
- Firebase-эмулятор: `firebase emulators:start --project demo-inform --only auth,database,hosting` → http://127.0.0.1:5000/?host. **Правила эмулятор сам не применяет** к namespace `demo-inform` — загрузить вручную:
  `curl -X PUT -H "Authorization: Bearer owner" --data-binary @database.rules.json "http://127.0.0.1:9000/.settings/rules.json?ns=demo-inform"`.
- `TaskStop` не убивает java-процессы эмулятора — добивать через `Get-CimInstance Win32_Process | ? CommandLine -match 'emulators:start|firebase-database-emulator'`. После тестов удалять `*-debug.log` в `quizzOnline/`.
- После тестов на живом сайте удалять тестовые комнаты (`deleteRoom(code)` с экрана учителя).
