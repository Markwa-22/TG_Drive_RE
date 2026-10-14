"""
Проверка подключения к Telegram (запускается через test_connection.bat).

Показывает: статус подключения, данные аккаунта, режим Telegram Premium
и лимит размера файла. API-ключи берутся из config.ini в корне проекта —
точно так же, как это делает main.py.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.ini")

OK = "[OK]"
ERR = "[!!]"
INFO = "[..]"


def read_api_credentials():
	"""Читает api_id/api_hash из config.ini (формат [pyrogram])."""
	api_id = None
	api_hash = None
	if not os.path.exists(CONFIG):
		return None, None
	try:
		with open(CONFIG, "r", encoding="utf-8") as file:
			for line in file:
				if "api_id" in line and "=" in line:
					api_id = line.split("=", 1)[1].strip()
				elif "api_hash" in line and "=" in line:
					api_hash = line.split("=", 1)[1].strip()
	except Exception as error:
		print(ERR, "Не удалось прочитать config.ini:", error)
	return api_id, api_hash


def main():
	print("=" * 60)
	print("            Test Connection - Telegram Cloud")
	print("=" * 60)
	print()

	api_id, api_hash = read_api_credentials()
	if not api_id or not api_hash:
		print(ERR, "config.ini не найден или в нём нет api_id/api_hash.")
		print(INFO, "Запустите приложение (start.bat) и войдите в аккаунт —")
		print(INFO, "файл config.ini будет создан автоматически.")
		return 1

	print(OK, "config.ini найден, api_id =", api_id)

	session_file = os.path.join(ROOT, "TelegramCloud.session")
	if os.path.exists(session_file):
		print(OK, "Файл сессии найден: TelegramCloud.session")
	else:
		print(INFO, "Файла сессии нет — вход будет запрошен приложением.")

	try:
		from pyrogram import Client
	except ImportError:
		print(ERR, "Pyrogram не установлен. Выполните: pip install -r requirements.txt")
		return 1

	app = Client("TelegramCloud", api_id=api_id, api_hash=api_hash, workdir=ROOT)
	print(INFO, "Подключаюсь к Telegram...")

	try:
		with app:
			me = app.get_me()
	except Exception as error:
		print()
		print(ERR, "Не удалось подключиться:", error)
		print(INFO, "Проверьте интернет и корректность api_id/api_hash,")
		print(INFO, "при необходимости сбросьте сессию: reset_settings.bat")
		return 1

	name = " ".join(part for part in [getattr(me, "first_name", None), getattr(me, "last_name", None)] if part)
	username = ("@" + me.username) if getattr(me, "username", None) else "—"
	is_premium = bool(getattr(me, "is_premium", False))

	print()
	print(OK, "Подключение успешно!")
	print("     ID         :", me.id)
	print("     Имя        :", name or "—")
	print("     Username   :", username)
	print("     Premium    :", "да" if is_premium else "нет")
	print("     Лимит файла:", "4 ГБ (3.9 ГБ на том)" if is_premium else "2 ГБ (1.9 ГБ на том)")
	print()
	print("=" * 60)
	return 0


if __name__ == "__main__":
	sys.exit(main())
