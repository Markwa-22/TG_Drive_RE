# Руководство по решению проблем

## 🚨 Быстрое решение (4 шага)

Если программа не запускается или файлы не загружаются:

### 1️⃣ Проверьте подключение
```bash
test_connection.bat
```
- ✅ **Успех** — всё в порядке, запускайте `start.bat`
- ❌ **Ошибка** — переходите к шагу 2

### 2️⃣ Сбросьте настройки
```bash
reset_settings.bat
```
Удаляет: API ключи, файл сессии, настройки программы.  
**Индекс файлов (`path.bd`) НЕ удаляется!**

### 3️⃣ Получите API ключи
1. Откройте https://my.telegram.org
2. Войдите с **вашим** номером телефона
3. Перейдите в **"API development tools"**
4. Создайте приложение (если нет)
5. Скопируйте:
   - **api_id** (число, напр. `12345678`)
   - **api_hash** (32 символа, напр. `1234567890abcdef1234567890abcdef`)

### 4️⃣ Запустите программу заново
```bash
start.bat
```
Введите: API ID → API Hash → Номер телефона → Код из Telegram → Пароль 2FA (если есть)

---

## 🔧 Утилиты

| Файл | Назначение |
|------|------------|
| `start.bat` | Быстрый запуск программы |
| `start_with_check.bat` | Запуск с проверкой системы (Python, зависимости, 7-Zip, БД) |
| `help.bat` | Интерактивное меню помощи |
| `test_connection.bat` | Проверка подключения к Telegram (показывает имя, username, Premium статус, лимиты) |
| `reset_settings.bat` | Полный сброс настроек и авторизации |

### Python скрипты
| Файл | Назначение |
|------|------------|
| `scripts/migrate_to_sqlite.py` | Необязательно: переносит индекс `path.bd` в SQLite (`tgdrive.db`). Приложение работает и без этого |
| `test_auth.py` | Используется внутри `test_connection.bat` |

---

## 📋 Частые проблемы и решения

### Ошибка: `The API key is required for new authorizations`
**Причина:** API ключи не передавались в клиент Pyrogram.  
**Исправлено в коде:** `main.py` теперь читает `config.ini` и передаёт ключи в `Client`.  
**Решение:** Запустите `reset_settings.bat` → `start.bat` → введите правильные ключи.

### Ошибка: `'NoneType' object has no attribute 'is_premium'`
**Причина:** После `app.start()` объект `app.me` был `None`.  
**Исправлено в коде:** Добавлен вызов `app.get_me()` после старта.  
**Решение:** То же — сброс настроек и повторная авторизация.

### Ошибка: `Python не найден` / `Модуль не найден`
**Решение:**
```bash
# Установите Python 3.8+ с python.org
pip install -r requirements.txt
```

### Ошибка: `7-Zip не найден`
**Решение:**
- Windows: `winget install 7zip.7zip` или скачайте с https://www.7-zip.org/
- Linux: `sudo apt install p7zip-full`

### Файлы >2GB не загружаются
**Решение:** Убедитесь что 7-Zip установлен. Программа автоматически разобьёт файл на тома (1.9GB для Standard, 3.9GB для Premium).

---

## 🔍 Подробная диагностика

### Проверка после исправления
После успешной авторизации запустите:
```bash
test_connection.bat
```
Должно показать:
```
✓ Успешно подключено!
  Имя: Ваше Имя
  Username: @ваш_username
  ID: ваш_id
  Телефон: +ваш_номер
  Premium: ✓ Да (лимит 4GB) или ✗ Нет (лимит 2GB)
```

### Если тест не проходит
1. Проверьте правильность API ID и API Hash (должны быть **вашими** с my.telegram.org)
2. Удалите `TelegramCloud.session` и авторизуйтесь заново
3. Проверьте интернет-соединение
4. Проверьте, не заблокирован ли аккаунт в Telegram

### Полный сброс (если ничего не помогает)
Удалите вручную:
- `config.ini`
- `TelegramCloud.session`
- `settings.json`

Затем запустите `start.bat` и введите всё с нуля.

---

## 📁 Структура файлов проекта

```
Telegram Cloud/
├── 🚀 Запуск
│   ├── start.bat                  # Быстрый запуск
│   ├── start_with_check.bat       # Запуск с проверкой системы
│   └── help.bat                   # Интерактивное меню
│
├── 🔧 Диагностика
│   ├── test_connection.bat        # Проверка подключения
│   └── reset_settings.bat         # Сброс настроек
│
├── 📚 Документация
│   ├── README.md                  # Полная документация (English)
│   ├── README.ru.md               # То же самое по-русски
│   ├── TROUBLESHOOTING.md         # Этот файл
│   └── CHANGELOG.md               # История изменений
│
├── 🐍 Код
│   ├── main.py                    # Точка входа (веб-интерфейс + логика)
│   └── scripts/                   # Python-модули
│       ├── archiver.py            # 7-Zip: упаковка, разбиение, распаковка
│       ├── pyrogram_optimizer.py  # Адаптивные чанки + FloodWait
│       ├── premium_detector.py    # Определение Telegram Premium
│       ├── upload_manager.py      # Высокоуровневый API загрузки (опционально)
│       ├── optimized_uploader.py  # Загрузчик на Telethon (опционально)
│       ├── database.py            # SQLite (опционально, не включено)
│       ├── migrate_to_sqlite.py   # Миграция path.bd → SQLite (опционально)
│       ├── encryption.py          # Опционально, не включено
│       └── test_auth.py           # Проверка подключения
│
├── Web/                           # Веб-интерфейс
└── 📁 Данные (создаются автоматически)
    ├── config.ini                 # API ключи       ← НЕ публиковать
    ├── TelegramCloud.session      # Сессия Telegram ← НЕ публиковать
    ├── settings.json              # Настройки       ← НЕ публиковать
    └── path.bd                    # Индекс файлов   ← НЕ публиковать
```

⚠️ Полный список того, что нельзя заливать в общий доступ, — в README
(раздел «Что НЕЛЬЗЯ заливать») и в файле `.gitignore`.

---

## 💡 Рекомендуемый порядок действий

### Первый запуск
```bash
start_with_check.bat
```
Программа сама проверит систему и установит всё необходимое.

### При проблемах
```bash
help.bat
# или
test_connection.bat
# если ошибка →
reset_settings.bat
start.bat
```

### Ежедневное использование
```bash
start.bat
```

---

## 📞 Полезные ссылки

- **API ключи:** https://my.telegram.org → API development tools
- **Python:** https://www.python.org/downloads/
- **7-Zip:** https://www.7-zip.org/
- **Оригинальный проект:** https://github.com/SuperZombi/Telegram_Cloud

---

## 📖 Связанная документация

- **README.md** — полное описание проекта (English) и **README.ru.md** (русский)
- **CHANGELOG.md** — история исправлений и новых функций
- **docs/prototype.html** — HTML-прототип нового интерфейса

---

*TG Drive RE — Безопасное облачное хранилище на базе Telegram*
