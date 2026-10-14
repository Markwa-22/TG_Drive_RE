# TG Drive RE — Telegram Cloud (Remastered)

A Windows desktop client that turns a **Telegram bot chat into your personal cloud**:
browse folders, upload and download files, pack large files into multi-volume 7-Zip
archives, preview images — from a modern dark/light web UI (Eel + Pyrogram).

Fork of [SuperZombi/Telegram_Cloud](https://github.com/SuperZombi/Telegram_Cloud) with a
redesigned interface and a tidied-up project layout.

> 🇷🇺 Русская версия: **[README.ru.md](README.ru.md)**

---

## ✨ Features

- **Folder tree inside Telegram** — the whole storage index lives in a single
  `path.bd` file; no server, no database service.
- **Upload**: single files, a whole folder, or several items at once.
- **Download**: one file (Save as…), a whole folder, or **a batch of selected files**
  into a folder you pick once.
- **Multi-volume archives**: files above the Telegram limit are split with 7-Zip into
  volumes and reassembled on download.
- **Telegram Premium detection** — 4 GB files (3.9 GB volumes) instead of 2 GB / 1.9 GB.
- **File management**: search, sorting (name / date), rename, move to another folder,
  delete (single, batch, and “delete empty folders”).
- **Image previews** with generated thumbnails (can be disabled for faster uploads).
- **Dark / light theme** and **Russian / English** interface.
- **Optimized uploader** — adaptive chunk sizes (64 KB – 512 KB) and automatic
  FloodWait retries.
- **Modern UI** built for this fork: header / sidebar / content / statusbar shell,
  **resizable sidebar** listing your root folders, memory-usage pill, selection
  counter, and per-row **type badges**: 📁 — an uploaded folder, 📦 — a multi-volume
  archive.

---

## 📋 Requirements

| | |
|---|---|
| OS | Windows 10/11 (Linux/macOS mostly work; BAT files are Windows-only) |
| Python | 3.8 or newer |
| 7-Zip | required for files above the Telegram limit and for packing folder uploads (`winget install 7zip.7zip`, or let `install.bat` do it) |
| Telegram | API ID + API Hash from <https://my.telegram.org> |

---

## 🚀 Install and run

**On Windows, the easy way:** double-click **`install.bat`** — it installs every dependency,
optionally into an isolated `.venv` folder, and checks 7-Zip (offering
`winget install 7zip.7zip`). Then start the app with `start.bat`.

**Manually:**

```bash
git clone https://github.com/<your-account>/<your-fork>.git
cd <your-fork>
python -m venv .venv                                  # optional but recommended
.venv\Scripts\python -m pip install -r requirements.txt
```

Windows launchers:

| File | What it does |
|---|---|
| `install.bat` | installs / updates dependencies (optionally into `.venv`) and checks 7-Zip |
| `start.bat` | starts the app |
| `start_with_check.bat` | checks Python, dependencies and 7-Zip first |
| `help.bat` | interactive menu (start / test / reset / install) |
| `test_connection.bat` | prints account info, Premium status and upload limits |
| `reset_settings.bat` | deletes `config.ini`, `TelegramCloud.session`, `settings.json` |

Or manually: `python main.py`. Every launcher prefers `.venv` when that folder exists and
falls back to the system Python otherwise, so both setups work. `.venv/` is in
`.gitignore` and is never published.

### First run

1. The login window asks for **phone number**, **api_id** and **api_hash**.
2. Enter the code Telegram sends to your account.
3. `config.ini` and `TelegramCloud.session` appear next to `main.py` — **keep them private**.

---

## 🗂 Project layout

```
Telegram Cloud/
├── main.py                    # entry point: Eel app + Telegram logic
├── scripts/                   # python modules (added to sys.path by main.py)
│   ├── archiver.py            # 7-Zip: packing, splitting, extraction
│   ├── pyrogram_optimizer.py  # adaptive chunks + FloodWait handling (used by main.py)
│   ├── premium_detector.py    # Premium detection helpers
│   ├── upload_manager.py      # higher-level upload API (optional)
│   ├── optimized_uploader.py  # Telethon-based uploader (optional, unused by default)
│   ├── database.py            # SQLite storage (optional, not wired into the app)
│   ├── migrate_to_sqlite.py   # path.bd → SQLite migration (optional)
│   ├── encryption.py          # optional, not wired into the app
│   └── test_auth.py           # connection test used by test_connection.bat
├── Web/                       # web UI: HTML / CSS / JS / icons
├── docs/prototype.html        # standalone UI prototype used for the redesign
├── requirements.txt
├── settings.json.example      # template for settings.json
└── *.bat                      # Windows launchers
```

`main.py` stays in the root on purpose (it is the entry point and resolves
`config.ini`, `path.bd` and the session file relative to itself); it adds `scripts/`
to `sys.path` so the modules inside can be imported as before.

---

## 📦 How folders and archives are stored

Everything in Telegram is a **file sent to a bot chat** — including things that look
like folders:

| You upload | Stored as | Shown in the list as |
|---|---|---|
| a folder | an archive (multi-volume if it is large) | folder icon + 📁 badge |
| a folder above the limit | a multi-volume archive | folder icon + 📦 📁 badges |
| a big file above the limit | a multi-volume archive | archive icon + 📦 badge |
| a normal file / archive | itself | archive or type icon, no badge |
| a folder created in the app | just a path in `path.bd` | folder icon, no badge |

That is why the same “archive” can show a folder badge: it *is* a folder on your disk,
packed for transport.

---

## ⚙️ settings.json

```json
{
  "lang": "RU",
  "theme": "dark",
  "show_preview": true,
  "preview_only_images": false,
  "updated_check_on_load": true,
  "sort_by": "by_alphabet",
  "premium_mode": "auto",
  "premium_detected": false
}
```

`settings.json.example` is the template; the real file is created on first run.
`lang` accepts `RU` / `EN`, `theme` accepts `dark` / `light`.

---

## ⛔ Never publish these files

They are already listed in `.gitignore` — verify with `git status` before your first push:

| File / folder | Why it must stay private |
|---|---|
| `config.ini` | your **api_id / api_hash** and phone number |
| `TelegramCloud.session` | the **Telegram session** — full access to your account |
| `path.bd` | your storage index: every file path and `message_id` in your cloud |
| `tgdrive.db` | the same index in SQLite form (if you enable it) |
| `settings.json` | your personal settings |
| `Temp/`, `Saves/` | temporary archives and previews — may contain your files |
| `Web.backup_pre_redesign/` | local backup of the previous UI |
| `__pycache__/`, `.venv/` | generated files |

If a session file ever leaks: Telegram → **Settings → Devices → terminate** that
session, then delete the file locally.

---

## 🛠 Troubleshooting

- **“API key is required for new authorizations”** — run `reset_settings.bat`, start
  again and re-enter the keys from <https://my.telegram.org>.
- **Nothing uploads over 2 GB** — 7-Zip is required for splitting; check it with
  `start_with_check.bat`.
- **“7-Zip not found”** — install it (`winget install 7zip.7zip`) or put `7z.exe` into
  a `tools/` folder next to `main.py`.
- **Login loop / weird session state** — `reset_settings.bat`, then `start.bat`.
- More: **TROUBLESHOOTING.md** (Russian).

---

## 📄 Documentation

| File | Language | Content |
|---|---|---|
| `README.md` | English | this file |
| `README.ru.md` | Russian | same content in Russian |
| `CHANGELOG.md` | Russian | history of changes |
| `TROUBLESHOOTING.md` | Russian | diagnosing common problems |
| `docs/prototype.html` | — | the standalone HTML prototype the new UI was built from |

---

## ⚖️ Credits and license

- Base project: [SuperZombi/Telegram_Cloud](https://github.com/SuperZombi/Telegram_Cloud)
- This fork: interface redesign, project cleanup, batch download, folder/archive badges.
- License: same as the original project.

Use at your own risk and keep backups of anything you cannot lose.
