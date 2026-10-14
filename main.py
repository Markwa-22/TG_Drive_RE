import asyncio
import sys
import warnings

# Suppress all deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Fix for Pyrogram 2.0.106 asyncio compatibility on Windows
if sys.platform == 'win32':
    # Use ProactorEventLoop for better Windows compatibility
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except RuntimeError:
        pass
else:
    # Create event loop for other platforms
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

from pyrogram import Client
from pyrogram.errors import FloodWait, BadRequest, UnknownError
from tkinter import Tk
from tkinter.filedialog import askopenfilenames, asksaveasfilename, askdirectory
import time
import eel
import os
import shutil
from PIL import Image
import cv2
import json
import tempfile
import subprocess
# --- Модули приложения лежат в scripts/ — добавляем папку в путь поиска ---
import os as _os, sys as _sys
_SCRIPTS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "scripts")
if _SCRIPTS_DIR not in _sys.path:
	_sys.path.insert(0, _SCRIPTS_DIR)

from archiver import SevenZipManager, MultiVolumeArchiver
from pyrogram_optimizer import get_optimizer

phone = ""
started = False
previews_show = True
preview_only_images = False
global_lang = "RU"
PATH = []
current_path = "/"
current_sort = "by_alphabet"
__version__ = 1.5
current_file_size = 0  # For download progress tracking
custom_temp_folder = None  # Custom temp folder path

# Initialize archiver for large files
sz_manager = None
archiver = None
try:
	sz_manager = SevenZipManager()
	archiver = MultiVolumeArchiver(sz_manager, is_premium=False)
	print(f"✅ 7-Zip найден: {sz_manager.seven_zip_path}")
except Exception as e:
	print(f"⚠️ 7-Zip не найден. Файлы >2GB не будут поддерживаться. Установите 7-Zip: https://www.7-zip.org/")
	print(f"   Ошибка: {e}")

# Initialize optimizer for upload/download speed optimization
optimizer = get_optimizer()
print("✅ Оптимизатор загрузки инициализирован (адаптивные чанки + умный FloodWait)")

CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice", "location", "contact",
                 "new_chat_members", "left_chat_member", "new_chat_title", "new_chat_photo", "delete_chat_photo",
                 "group_chat_created", "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id",
                 "migrate_from_chat_id", "pinned_message"]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'}


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def executable_path(to_where="folder"):
	_path = os.path.abspath(__file__)
	
	if to_where == "file":
		return _path

	_path = _path.split("\\")
	_path = _path[0:-1]

	final_path = ""
	for i in range(len(_path)):
		final_path += _path[i]
		if i != len(_path)-1:
			final_path += "\\"

	return final_path

def format_file_size(bytes_size):
	"""Format file size in human-readable format"""
	for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
		if bytes_size < 1024.0:
			return f"{bytes_size:.2f} {unit}"
		bytes_size /= 1024.0
	return f"{bytes_size:.2f} PB"

def get_temp_dir(prefix="tgdrive_"):
	"""Get temporary directory path (custom or system default)"""
	global custom_temp_folder
	if custom_temp_folder and os.path.exists(custom_temp_folder):
		temp_path = os.path.join(custom_temp_folder, prefix + os.urandom(8).hex())
		os.makedirs(temp_path, exist_ok=True)
		return temp_path
	else:
		return tempfile.mkdtemp(prefix=prefix)

# ============================================
# ASYNC HELPER FUNCTIONS
# ============================================

def run_async(coro):
	"""Запустить async функцию в существующем event loop"""
	loop = asyncio.get_event_loop()
	return loop.run_until_complete(coro)

async def run_in_executor(func, *args):
	"""Запустить синхронную функцию в executor"""
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(None, func, *args)

async def run_subprocess_async(cmd, **kwargs):
	"""Запустить subprocess асинхронно"""
	loop = asyncio.get_event_loop()
	return await loop.run_in_executor(None, lambda: subprocess.run(cmd, **kwargs))

def cleanup_old_temp_folders():
	"""Clean up old temporary folders left from previous sessions"""
	global custom_temp_folder
	import time
	
	# List of directories to check
	dirs_to_check = []
	
	# Add custom temp folder if set
	if custom_temp_folder and os.path.exists(custom_temp_folder):
		dirs_to_check.append(custom_temp_folder)
	
	# Add system temp folder
	dirs_to_check.append(tempfile.gettempdir())
	
	cleaned_count = 0
	for temp_base in dirs_to_check:
		try:
			for item in os.listdir(temp_base):
				# Check if it's a tgdrive temp folder
				if item.startswith("tgdrive_"):
					folder_path = os.path.join(temp_base, item)
					if os.path.isdir(folder_path):
						try:
							# Check if folder is older than 1 hour
							folder_age = time.time() - os.path.getmtime(folder_path)
							if folder_age > 3600:  # 1 hour
								shutil.rmtree(folder_path)
								cleaned_count += 1
								print(f"🧹 Удалена старая временная папка: {item}")
						except Exception as e:
							# Skip if we can't delete (might be in use)
							pass
		except Exception as e:
			# Skip if we can't access the directory
			pass
	
	if cleaned_count > 0:
		print(f"✅ Очищено старых временных папок: {cleaned_count}")
	else:
		print("✅ Старые временные папки не найдены")

def load_langs():
	global LANGUAGES
	with open(resource_path("Web\\languages.json"), 'r', encoding = 'utf-8') as file:
		lines = file.read().split("=")
		lines = '{"'+lines[0].replace(" ",'')+'":'+lines[1]+"}"
		lines = lines.replace("/", '')
		LANGUAGES = json.loads(lines)['LANGUAGES']
load_langs()

@eel.expose
def get_global_lang():
	global global_lang
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())
			global_lang = lines["lang"]
			return lines["lang"]

	except:
		return

@eel.expose
def change_lang(lang):
	global global_lang
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())

	except FileNotFoundError:
		lines = {}

	lines["lang"] = lang
	global_lang = lang
	with open('settings.json', 'w', encoding = 'utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))	

@eel.expose
def show_preview_setting():
	global previews_show
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())
			previews_show = lines["show_preview"]
			return lines["show_preview"]

	except:
		return True

@eel.expose
def save_preview_settings(val):
	global previews_show
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())

	except FileNotFoundError:
		lines = {}

	lines["show_preview"] = val
	previews_show = val
	with open('settings.json', 'w', encoding = 'utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))

@eel.expose
def get_preview_only_images():
	global preview_only_images
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())
			preview_only_images = lines["preview_only_images"]
			return lines["preview_only_images"]

	except:
		return False

@eel.expose
def save_preview_only_images(val):
	global preview_only_images
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())

	except FileNotFoundError:
		lines = {}

	lines["preview_only_images"] = val
	preview_only_images = val
	with open('settings.json', 'w', encoding = 'utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))	

def save_sorting():
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())

	except FileNotFoundError:
		lines = {}

	lines["sort_by"] = current_sort
	with open('settings.json', 'w', encoding = 'utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))

@eel.expose
def sort_by(what):
	global current_sort
	if what == current_sort:
		current_sort = str(what) + "_reverse"
	else:
		current_sort = what
	save_sorting()

@eel.expose()
def get_curent_arrow():
	global current_sort
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())
			current_sort = lines["sort_by"]

	except:
		current_sort = "by_alphabet"
	return current_sort

@eel.expose
def create_config(api_id, api_hash, phone_number):
	global phone
	phone = phone_number
	with open(executable_path()+'\\config.ini', 'w') as file:
		file.write('[pyrogram]\napi_id = ' + str(api_id) + "\napi_hash = "+ str(api_hash))


@eel.expose
def starting():
	"""Синхронная обертка для Eel"""
	return run_async(starting_async())

async def starting_async():
	"""Async версия инициализации"""
	global phone, started, app
	first_time = False
	if not started:
		# Load temp folder setting at startup
		load_temp_folder_setting()
		
		# ✅ ИЗМЕНЕНИЕ: Async очистка старых папок
		await run_in_executor(cleanup_old_temp_folders)
		
		# Read API credentials from config.ini
		config_path = executable_path() + '\\config.ini'
		api_id = None
		api_hash = None
		
		try:
			with open(config_path, 'r') as f:
				for line in f:
					if 'api_id' in line:
						api_id = line.split('=')[1].strip()
					elif 'api_hash' in line:
						api_hash = line.split('=')[1].strip()
		except FileNotFoundError:
			pass
		
		if phone == "":
			if api_id and api_hash:
				app = Client("TelegramCloud", api_id=api_id, api_hash=api_hash)
			else:
				app = Client("TelegramCloud")
		else:
			first_time = True
			if api_id and api_hash:
				app = Client("TelegramCloud", api_id=api_id, api_hash=api_hash, phone_number=phone)
			else:
				app = Client("TelegramCloud", phone_number=phone)
		started = True
		
		# ✅ ИЗМЕНЕНИЕ: Async start
		await app.start()
		
		# Ensure client has loaded user info
		if app.me is None:
			try:
				# Force load user info
				await app.get_me()
			except:
				pass
		
		if first_time:
			await app.send_message('TelegCloudyBot', "/start")

@eel.expose
def check_theme():
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())
			return lines["theme"]

	except:
		return

@eel.expose
def save_theme(theme_name):
	try:
		with open('settings.json', 'r', encoding = 'utf-8') as file:
			lines = json.loads(file.read())

	except FileNotFoundError:
		lines = {}

	lines["theme"] = theme_name
	with open('settings.json', 'w', encoding = 'utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))

@eel.expose
def get_path():
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	files = askopenfilenames(parent=root)
	return files

@eel.expose
def get_folder():
	"""Выбор папки для загрузки"""
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	folder = askdirectory(parent=root)
	return folder if folder else None

@eel.expose
def get_multiple_items():
	"""Выбор нескольких файлов и папок для загрузки"""
	import tkinter as tk
	from tkinter import messagebox
	
	all_items = []
	
	# Создаем главное окно для диалогов
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	
	# Шаг 1: Выбор файлов
	files = askopenfilenames(parent=root, title="Выберите файлы (или нажмите Отмена для пропуска)")
	if files:
		all_items.extend(list(files))
	
	# Шаг 2: Спросить, нужно ли добавить папки
	if messagebox.askyesno("Добавить папки?", "Хотите добавить папки к загрузке?", parent=root):
		while True:
			folder = askdirectory(parent=root, title="Выберите папку (или нажмите Отмена для завершения)")
			if folder:
				all_items.append(folder)
				# Спросить, добавить ли еще папки
				if not messagebox.askyesno("Добавить еще?", "Добавить еще одну папку?", parent=root):
					break
			else:
				break
	
	root.destroy()
	return all_items if all_items else None

@eel.expose
def get_temp_folder():
	"""Выбор кастомной папки для временных файлов"""
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	folder = askdirectory(parent=root, title="Выберите папку для временных файлов")
	return folder if folder else None

@eel.expose
def save_temp_folder(folder_path):
	"""Сохранить путь к кастомной temp папке"""
	global custom_temp_folder, archiver, sz_manager
	try:
		with open('settings.json', 'r', encoding='utf-8') as file:
			lines = json.loads(file.read())
	except FileNotFoundError:
		lines = {}
	
	lines["temp_folder_path"] = folder_path
	custom_temp_folder = folder_path if folder_path else None
	
	# Reinitialize archiver with new temp folder
	if sz_manager:
		archiver = MultiVolumeArchiver(sz_manager, is_premium=False, custom_temp_folder=custom_temp_folder)
	
	with open('settings.json', 'w', encoding='utf-8') as file:
		file.write(json.dumps(lines, ensure_ascii=False, indent=2))
	
	return True

@eel.expose
def get_temp_folder_setting():
	"""Получить сохраненный путь к temp папке"""
	try:
		with open('settings.json', 'r', encoding='utf-8') as file:
			lines = json.loads(file.read())
			return lines.get("temp_folder_path", "")
	except:
		return ""

@eel.expose
def load_temp_folder_setting():
	"""Загрузить настройку temp папки при старте"""
	global custom_temp_folder, archiver, sz_manager
	try:
		with open('settings.json', 'r', encoding='utf-8') as file:
			lines = json.loads(file.read())
			temp_path = lines.get("temp_folder_path", "")
			if temp_path and os.path.exists(temp_path):
				custom_temp_folder = temp_path
				# Reinitialize archiver with custom temp folder
				if sz_manager:
					archiver = MultiVolumeArchiver(sz_manager, is_premium=False, custom_temp_folder=custom_temp_folder)
				print(f"📁 Используется кастомная temp папка: {temp_path}")
				return temp_path
	except:
		pass
	return ""

async def progress(current, total, client):
	global x, y, stop_transmit
	stop_transm = eel.progres(x, y, round(current * 100 / total, 1))()
	if stop_transm:
		print(LANGUAGES[global_lang]["python"]["download_cancel"])
		stop_transmit = True
		client.stop_transmission()
	print(str(x) + "/" + str(y) + " : " + str(round(current * 100 / total, 1)) + "%")


def file_exists(file):
	global PATH
	for i in PATH:
		if i == file:
			return True
	return False


@eel.expose
def read_path():
	global PATH
	PATH = []
	try:
		with open('path.bd', 'r', encoding = 'utf-8') as file:
			F = file.readlines()
			for i in F:
				PATH.append(json.loads(i)[0])

		return PATH
	except:
		None

def create_preview(file):
	index = file.split(".")[-1].lower()
	type_of_file = ""
	for i in file_types:
		for x in i:
			if x == index:
				type_of_file = file_types_str[file_types.index(i)]
				break
	if type_of_file == "image":
		print(LANGUAGES[global_lang]["python"]["generating_preview"])
		try:
			os.makedirs("Temp")
		except:
			None
		img = Image.open(file)
		img = img.resize((int(400*img.width/img.height), 400))
		img.save('Temp\\resized_image.'+index)
		return 'Temp\\resized_image.'+index
	if not preview_only_images:
		if type_of_file == "video":
			print(LANGUAGES[global_lang]["python"]["generating_preview"])
			try:
				os.makedirs("Temp")
			except:
				None
			vidcap = cv2.VideoCapture(file)
			success,image = vidcap.read()
			cv2.imwrite("Temp\\frame.png", image)
			img = Image.open("Temp\\frame.png")
			img = img.resize((int(400*img.width/img.height), 400))
			img.save('Temp\\resized_image.png')
			return 'Temp\\resized_image.png'
	return

@eel.expose
def upload(array, path):
	"""Синхронная обертка для Eel"""
	return run_async(upload_async(array, path))

async def upload_async(array, path):
	"""Async версия загрузки файлов"""
	logs = []
	global x, y, PATH, stop_transmit, archiver
	stop_transmit = False
	x = 1
	y = len(array)
	read_path()
	for i in array:
		splited = i.split('/')
		name = splited[-1]
		path_ = str(path) + str(name)

		if file_exists(path_):
			tmp_ = i.split("/")[-1]
			logs.append(LANGUAGES[global_lang]["python"]["file"] + str(tmp_) + LANGUAGES[global_lang]["python"]["already_exist"])
			print("  "+LANGUAGES[global_lang]["python"]["file"] + str(i) + LANGUAGES[global_lang]["python"]["already_exist"])
			x+=1
			continue

		print(i)
		
		# Check if it's a directory
		is_directory = os.path.isdir(i)
		temp_dir = None
		multi_temp_dir = None
		volumes = []
		is_multivolume = False
		is_folder_archive = False
		
		# If it's a directory, create archive first
		if is_directory:
			if not archiver:
				error_msg = f"❌ Невозможно загрузить папку {name}: 7-Zip не установлен"
				print(error_msg)
				logs.append(error_msg)
				x += 1
				continue
			
			is_folder_archive = True
			print(f"📁 Архивирование папки: {name}")
			
			# Create temporary archive of the folder
			temp_dir = get_temp_dir(prefix="tgdrive_folder_")
			archive_path = os.path.join(temp_dir, f"{name}.7z")
			
			try:
				# Create archive with compression
				cmd = [
					archiver.sz.seven_zip_path,
					"a",  # Add to archive
					"-mx=5",  # Normal compression
					"-mmt=on",  # Multi-threading
					archive_path,
					i + "\\*"  # All contents of folder
				]
				
				result = await run_subprocess_async(cmd, capture_output=True, timeout=3600)
				if result.returncode != 0:
					raise Exception(f"Ошибка архивирования: {result.stderr.decode('utf-8', errors='ignore')}")
				
				print(f"✅ Папка заархивирована: {format_file_size(os.path.getsize(archive_path))}")
				
				# Now use this archive as the file to upload
				i = archive_path
				file_size = os.path.getsize(i)
				
			except Exception as e:
				error_msg = f"❌ Ошибка архивирования папки {name}: {str(e)}"
				print(error_msg)
				logs.append(error_msg)
				if temp_dir and os.path.exists(temp_dir):
					await run_in_executor(shutil.rmtree, temp_dir)
				x += 1
				continue
		else:
			file_size = os.path.getsize(i)
		
		try:
			if archiver and archiver.needs_splitting(i):
				is_multivolume = True
				print(f"📦 Файл больше 2GB ({format_file_size(file_size)}), создание многотомного архива...")
				
				# Create multi-volume archive
				volumes, multi_temp_dir = await run_in_executor(archiver.create_archive, i)
				print(f"✅ Создано томов: {len(volumes)}")
				
				# ✅ ГЛАВНОЕ ИЗМЕНЕНИЕ: Параллельная загрузка томов
				print(f"🚀 Параллельная загрузка {len(volumes)} томов...")
				
				async def upload_volume(vol_idx, vol_path):
					"""Загрузить один том"""
					print(f"📤 Загрузка тома {vol_idx}/{len(volumes)}: {os.path.basename(vol_path)}")
					
					# ✅ ОПТИМИЗАЦИЯ: Используем оптимизированную загрузку для томов
					vol_message = await optimizer.upload_with_retry(
						app,
						'TelegCloudyBot',
						vol_path,
						caption=f"📦 {name} - Том {vol_idx}/{len(volumes)}",
						progress_callback=lambda c, t, s, stats: progress(c, t, app),
						use_adaptive_chunking=True,
						max_retries=5
					)
					
					return {
						'volume_number': vol_idx,
						'message_id': vol_message.id,
						'file_id': vol_message.document.file_id,
						'file_size': vol_message.document.file_size
					}
				
				# Загружаем все тома параллельно
				upload_tasks = [
					upload_volume(vol_idx, vol_path) 
					for vol_idx, vol_path in enumerate(volumes, 1)
				]
				
				volume_messages = await asyncio.gather(*upload_tasks)
				
				if stop_transmit:
					# Cleanup before returning
					if multi_temp_dir and os.path.exists(multi_temp_dir):
						await run_in_executor(shutil.rmtree, multi_temp_dir)
					if temp_dir and os.path.exists(temp_dir):
						await run_in_executor(shutil.rmtree, temp_dir)
					return logs
				
				# Save multivolume metadata to path.bd
				multivolume_data = {
					'is_multivolume': True,
					'is_folder': is_folder_archive,
					'original_name': name,
					'original_size': file_size,
					'volumes': volume_messages,
					'total_volumes': len(volumes)
				}
				
				# ✅ ИЗМЕНЕНИЕ: Async запись в файл
				import aiofiles
				async with aiofiles.open('path.bd', 'a', encoding='utf-8') as file:
					await file.write(json.dumps([path_, multivolume_data], ensure_ascii=False) + "\n")
				
				print(f"✅ Многотомный файл загружен: {name} ({len(volumes)} томов)")
				
				# Cleanup multi-volume temp dir
				if multi_temp_dir and os.path.exists(multi_temp_dir):
					await run_in_executor(shutil.rmtree, multi_temp_dir)
				
			else:
				# Normal upload for files < 2GB or small folders
				# Add folder indicator to caption if it's a folder archive
				caption = f"📁 {name}" if is_folder_archive else None
				
				# ✅ ОПТИМИЗАЦИЯ: Используем оптимизированную загрузку с адаптивными чанками и FloodWait
				print(f"🚀 Оптимизированная загрузка: {name}")
				message = await optimizer.upload_with_retry(
					app,
					'TelegCloudyBot',
					i,
					caption=caption,
					progress_callback=lambda c, t, s, stats: progress(c, t, app),
					use_adaptive_chunking=True,
					max_retries=5
				)
				if stop_transmit:
					# Cleanup before returning
					if temp_dir and os.path.exists(temp_dir):
						await run_in_executor(shutil.rmtree, temp_dir)
					return logs
				msg_id = message.id  # Pyrogram 2.x uses 'id' not 'message_id'
				
				# Initialize preview variables
				f2 = None
				preview_msg_id = None
				preview_file_id = None
				
				if previews_show and not is_folder_archive:
					f2 = create_preview(i)
					if f2:
						f2_ = open(str(f2), "rb")
						preview = await app.send_document('TelegCloudyBot', f2_)
						try:
							await run_in_executor(shutil.rmtree, "Temp\\")
						except:
							None
						preview_msg_id = preview.id  # Pyrogram 2.x uses 'id' not 'message_id'
						preview_file_id = preview.document.file_id
				
				# Extract file metadata from Pyrogram 2.x message object
				file_id = None
				size = None
				
				# Try to get document info (Pyrogram 2.x uses attributes, not dict access)
				if hasattr(message, 'document') and message.document:
					file_id = message.document.file_id
					size = message.document.file_size
				elif hasattr(message, 'video') and message.video:
					file_id = message.video.file_id
					size = message.video.file_size
				elif hasattr(message, 'audio') and message.audio:
					file_id = message.audio.file_id
					size = message.audio.file_size
				elif hasattr(message, 'photo') and message.photo:
					file_id = message.photo.file_id
					size = message.photo.file_size
				
				# Build message metadata
				if file_id and size:
					msg = {'file_id': file_id, 'file_size': size, 'message_id': msg_id, 'is_folder': is_folder_archive}
					if previews_show and f2 and preview_msg_id and preview_file_id:
						msg['preview_message_id'] = preview_msg_id
						msg['preview_file_id'] = preview_file_id
					
					import aiofiles
					async with aiofiles.open('path.bd', 'a', encoding='utf-8') as file:
						await file.write(json.dumps([path_, msg], ensure_ascii=False) + "\n")
				else:
					print(f"Warning: Could not extract file metadata for {name}")
				
				print(LANGUAGES[global_lang]["python"]["file"] + str(i) + LANGUAGES[global_lang]["python"]["uploaded"])
				logs.append(LANGUAGES[global_lang]["python"]["file"] + str(i.split("/")[-1]) + LANGUAGES[global_lang]["python"]["uploaded"])
			
			x += 1
			
		except Exception as e:
			error_msg = f"❌ Ошибка загрузки {name}: {str(e)}"
			print(error_msg)
			logs.append(error_msg)
			x += 1
			
		finally:
			# Cleanup temporary archive files
			if temp_dir and os.path.exists(temp_dir):
				try:
					await run_in_executor(shutil.rmtree, temp_dir)
				except:
					pass
			# Cleanup multi-volume temp dir if it wasn't cleaned up earlier
			if multi_temp_dir and os.path.exists(multi_temp_dir):
				try:
					await run_in_executor(shutil.rmtree, multi_temp_dir)
				except:
					pass

	return logs
		

@eel.expose
def get_saved_path():
	global current_path
	return current_path

@eel.expose
def save_current_path(path):
	global current_path
	current_path = path


@eel.expose
def build_path(path):
	global current_sort
	array = read_path()
	if array:
		temp_path = path.split("/")[1:-1]
		c = []
		for i in array:
			temp = i.split("/")[1:]
			if len(temp_path) == 0:
				c.append(temp)
			else:
				for x in range(len(temp)-1):
					try:
						if temp_path[x] == temp[x]:
							if x == len(temp_path)-1:
								c.append(temp)
						else:
							break
					except:
						break

		folders = []
		files = []
		for i in c:
			for x in range(len(temp_path)):
				i.pop(0)

			if len(i) == 1:
				if i[0] != "":
					files.append(i[0])
			else:
				if not i[0] in folders:
					folders.append(i[0])

		if current_sort == "by_alphabet":
			return {'folders': sorted(folders), 'files': sorted(files)}
		if current_sort == "by_alphabet_reverse":
			folders = sorted(folders)
			folders.reverse()
			files = sorted(files)
			files.reverse()
			return {'folders': folders, 'files': files}
		if current_sort == "by_date":
			return {'folders': folders, 'files': files}
		if current_sort == "by_date_reverse":
			folders.reverse()
			files.reverse()
			return {'folders': folders, 'files': files}

@eel.expose
def create_folder(path):
	with open('path.bd', 'a', encoding = 'utf-8') as file:
		file.write(json.dumps([path], ensure_ascii=False) + "\n")

def path_index(path, PATH=None):
	"""Индекс записи в path.bd.
	Папки в базе хранятся с завершающим слэшем ('/Test/'), а интерфейс
	строит путь без него ('/Test/sosal 1'), поэтому пробуем несколько форм
	вместо PATH.index(path), который в такой ситуации падает с ValueError."""
	if PATH is None:
		PATH = read_path()
	if not PATH:
		return None
	for cand in (path, path + "/", path.rstrip("/"), path.rstrip("/") + "/"):
		try:
			return PATH.index(cand)
		except ValueError:
			continue
	return None


@eel.expose
def delete_file(path):
	PATH = read_path()
	with open('path.bd', 'r', encoding = 'utf-8') as file:
		F = file.readlines()

	idx = path_index(path, PATH)
	if idx is None:
		print("⚠️ delete_file: путь не найден в path.bd: " + str(path))
		return False
	file_data = json.loads(F[idx])[1]
	
	# Check if this is a multivolume file
	if isinstance(file_data, dict) and file_data.get('is_multivolume'):
		# Delete all volumes
		print(f"🗑️ Удаление многотомного файла: {file_data['original_name']}")
		volumes = file_data.get('volumes', [])
		for vol in volumes:
			try:
				app.delete_messages('TelegCloudyBot', vol['message_id'])
				print(f"   Удален том {vol['volume_number']}/{len(volumes)}")
			except Exception as e:
				print(f"   Ошибка удаления тома {vol['volume_number']}: {e}")
	else:
		# Normal single file deletion
		try:
			id_ = file_data['message_id']
			app.delete_messages('TelegCloudyBot', id_)
		except Exception as e:
			print(LANGUAGES[global_lang]["python"]["error_1"] + str(path) + LANGUAGES[global_lang]["python"]["error_2"])
		
		# Delete preview if exists
		try:
			id_pre = file_data['preview_message_id']
			app.delete_messages('TelegCloudyBot', id_pre)
		except:
			None
	
	# Remove from path.bd
	F.pop(idx)
	str_ = ""
	for i in F:
		str_ += str(i)

	with open('path.bd', 'w', encoding = 'utf-8') as file:
		file.write(str_)

@eel.expose
def delete_folder(path):
	array = read_path()

	temp_path = path.split("/")[1:-1]
	c = []
	for i in array:
		temp = i.split("/")[1:]
		if len(temp_path) == 0:
			c.append(temp)
		else:
			for x in range(len(temp)-1):
				try:
					if temp_path[x] == temp[x]:
						if x == len(temp_path)-1:
							c.append(temp)
					else:
						break
				except:
					break

	temp_str = []
	for i in range(len(c)):
		temp = "/"
		for x in c[i]:
			temp += str(x) + "/"
		temp = temp[:-1]
		temp_str.append(temp)


	with open('path.bd', 'r', encoding = 'utf-8') as file:
		F = file.readlines()

	PATH = array

	for i in temp_str:
		try:
			id_ = json.loads(F[PATH.index(i)])[1]['message_id']
			try:
				app.delete_messages('TelegCloudyBot', id_)
			except:
				print(LANGUAGES[global_lang]["python"]["error_1"] + str(i) + LANGUAGES[global_lang]["python"]["error_2"])
			try:
				id_pre = json.loads(F[PATH.index(i)])[1]['preview_message_id']
				app.delete_messages('TelegCloudyBot', id_pre)	
			except:
				None
		except:
			#this is folder (not a file)
			None
		
		F.pop(PATH.index(i))
		PATH.pop(PATH.index(i))

	str_ = ""
	for x in F:
		str_ += str(x)

	with open('path.bd', 'w', encoding = 'utf-8') as file:
		file.write(str_)
	


@eel.expose
def rename_file(old, new):
	PATH = read_path()
	with open('path.bd', 'r', encoding = 'utf-8') as file:
		F = file.readlines()

	idx = path_index(old, PATH)
	if idx is None:
		print("⚠️ rename_file: путь не найден в path.bd: " + str(old))
		return False
	temp_el = json.loads(F[idx])
	temp_el[0] = new

	F[idx] = json.dumps(temp_el, ensure_ascii=False) + "\n"

	str_ = ""
	for i in F:
		str_ += str(i)

	with open('path.bd', 'w', encoding = 'utf-8') as file:
		file.write(str_)


@eel.expose
def rename_folder(old, new):
	array = read_path()

	temp_path = old.split("/")[1:-1]
	c = []
	for i in array:
		temp = i.split("/")[1:]
		if len(temp_path) == 0:
			c.append(temp)
		else:
			for x in range(len(temp)-1):
				try:
					if temp_path[x] == temp[x]:
						if x == len(temp_path)-1:
							c.append(temp)
					else:
						break
				except:
					break

	temp_str = []
	for i in range(len(c)):
		temp = "/"
		for x in c[i]:
			temp += str(x) + "/"
		temp = temp[:-1]
		temp_str.append(temp)

	new_arr = []
	for i in temp_str:
		x = i.split(old)
		new_arr.append(str(new) + x[1])


	with open('path.bd', 'r', encoding = 'utf-8') as file:
		F = file.readlines()

	PATH = array
	for i in range(len(temp_str)):
		temp_el = json.loads(F[PATH.index(temp_str[i])])
		temp_el[0] = new_arr[i]

		F[PATH.index(temp_str[i])] = json.dumps(temp_el, ensure_ascii=False) + "\n"

	str_ = ""
	for i in F:
		str_ += str(i)

	with open('path.bd', 'w', encoding = 'utf-8') as file:
		file.write(str_)


def srawn(array1, array2):
	for i in range(len(array1)):
		try:
			if array1[i] != array2[i]:
				return False
		except:
			None
	return True

@eel.expose
def delete_empty_folders(path):
	PATH = read_path()

	temp_path = path.split("/")[1:-1]
	c = []
	for i in PATH:
		temp = i.split("/")[1:]
		if temp[-1] == "":
			if srawn(temp, temp_path):
				if path != i:
					c.append(i)

	if len(c) != 0:
		with open('path.bd', 'r', encoding = 'utf-8') as file:
			F = file.readlines()

		for i in c:
			F.pop(PATH.index(i))
			PATH.pop(PATH.index(i))

		str_ = ""
		for x in F:
			str_ += str(x)

		with open('path.bd', 'w', encoding = 'utf-8') as file:
			file.write(str_)


archives = [
	'rar', 'zip', 'tar', 'gz'
]
audio = [
	'au', 'mp3', 'mp2', 'wav', 'midi', 'wma', 'flac', 'aac', 'ogg' 
]
image = [
	'gif', 'jpg', 'jpeg', 'png', 'svg', 'ico', 'webp', 'bmp', 'tif'
]
video = [
	'mp4', 'mpeg', 'mov', 'webm', 'avi', 'movie', 'mkv', 'mpg', 'flv', 'wmv'
]
code = [
	'php', 'scala', 'java', 'cpp', 'cs', 'js', 'json', 'css', 'csv', 'html', 'c', 'h', 'py', 'xml', 'xsl', 'bat'
]
binary = [
	'bin', 'dll', 'exe', 'o', 'pyc', 'pyo'
]
document = [
	'doc', 'pdf', 'xls', 'ppt', 'txt'
]

file_types = [archives, audio, image, video, code, binary, document]
file_types_str = ['archive', 'audio', 'image', 'video', 'code', 'binary', 'document']
file_types_image = ["images/archive.png", "images/audio.png", "images/image.png", "images/video.png", "images/code.png", "images/binary.png", "images/document.png"]


@eel.expose
def file_type(name):
	default = "images/file.png"
	
	# Check if this file is marked as a folder in the database
	try:
		PATH = read_path()
		# Try exact match first
		if name in PATH:
			with open('path.bd', 'r', encoding = 'utf-8') as file_:
				F = file_.readlines()
			temp = json.loads(F[PATH.index(name)])[1]
			if isinstance(temp, dict) and temp.get('is_folder', False):
				# Загруженная папка остаётся с иконкой папки (как и раньше);
				# её тип видно по значку 📁 у названия строки
				return "images/folder.png"
		else:
			# If not exact match, try to find by filename (for cases where only filename is passed)
			with open('path.bd', 'r', encoding = 'utf-8') as file_:
				F = file_.readlines()
			for idx, path in enumerate(PATH):
				# Check if the path ends with the given name
				if path.endswith("/" + name) or path == "/" + name:
					temp = json.loads(F[idx])[1]
					if isinstance(temp, dict) and temp.get('is_folder', False):
						return "images/folder.png"
					break
	except Exception as e:
		pass
	
	try:
		index = name.split(".")[-1].lower()
	except:
		return default
	for i in file_types:
		for x in i:
			if x == index:
				return file_types_image[file_types.index(i)]
	return default

@eel.expose
def download_dir(file):
	# Check if it's a folder from path.bd
	try:
		PATH = read_path()
		with open('path.bd', 'r', encoding='utf-8') as file_:
			F = file_.readlines()
		
		temp = json.loads(F[PATH.index(file)])[1]
		
		# Check if it's a folder (normal or multivolume)
		is_folder = False
		if isinstance(temp, dict):
			if temp.get('is_folder', False):
				is_folder = True
			elif temp.get('is_multivolume', False) and temp.get('is_folder', False):
				is_folder = True
	except:
		is_folder = False
	
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	
	if is_folder:
		# For folders, use askdirectory to select destination folder
		folder_name = file.split("/")[-1]
		directory = askdirectory(parent=root, title=f"Выберите папку для сохранения '{folder_name}'")
		return directory if directory else None
	else:
		# For files, use asksaveasfilename
		type_ = file_type(file)
		type_name = type_.split('/')[-1].split(".")[0].title()
		try:
			type_format = '*.' + file.split(".")[-1]
		except:
			type_format = "*.*"
		
		askfile = asksaveasfilename(parent=root, initialfile=file.split("/")[-1], filetypes=[(type_name, type_format), ("All files", "*.*")])
		
		if askfile == "" or askfile == None:
			return None
		
		if askfile.split(".")[-1] == file.split(".")[-1]:
			return askfile
		else:
			return askfile + "." + file.split(".")[-1]

@eel.expose
def choose_directory(title=None):
	"""Диалог выбора папки — нужен для скачивания сразу нескольких файлов."""
	root = Tk()
	root.withdraw()
	root.wm_attributes('-topmost', 1)
	directory = askdirectory(parent=root, title=title or "Выберите папку для сохранения")
	return directory if directory else None


@eel.expose
def is_folder_entry(path):
	"""True, если запись — загруженная (упакованная) папка, а не обычный файл.
	Для таких записей второй аргумент download() — папка, а не путь к файлу."""
	try:
		PATH = read_path()
		with open('path.bd', 'r', encoding = 'utf-8') as file_:
			F = file_.readlines()
		idx = path_index(path, PATH)
		if idx is None:
			return False
		temp = json.loads(F[idx])[1]
		return bool(isinstance(temp, dict) and temp.get('is_folder', False))
	except:
		return False


def entry_markers(temp):
	"""Значки записи — тот же порядок, что в file_size():
	📦 — многотомный архив, 📁 — загруженная (упакованная) папка."""
	if not isinstance(temp, dict):
		return ""
	markers = ""
	if temp.get('is_multivolume', False):
		markers += "📦"
	if temp.get('is_folder', False):
		markers += " 📁"
	return markers.strip()


@eel.expose
def entry_badges(name):
	"""Значки 📁/📦 для строки списка (без размера) — дублируют то, что
	видно в окне предпросмотра, чтобы не открывать файл ради этого."""
	try:
		PATH = read_path()
		with open('path.bd', 'r', encoding = 'utf-8') as file_:
			F = file_.readlines()
		idx = None
		if name in PATH:
			idx = PATH.index(name)
		else:
			for i, p in enumerate(PATH):
				if p.endswith("/" + name) or p == "/" + name:
					idx = i
					break
		if idx is None:
			return ""
		return entry_markers(json.loads(F[idx])[1])
	except:
		return ""


def progress2(current, total, file_size=None):
	"""Progress callback для скачивания"""
	if file_size and file_size > 0:
		x = round(current * 100 / file_size, 1)
	elif total and total > 0:
		x = round(current * 100 / total, 1)
	else:
		x = 0
	
	if x > 100:
		x = 100
	eel.change_progress(x)
	print(str(x) + "%")


@eel.expose
def download(file, directory):
	"""Синхронная обертка для Eel"""
	# directory is actually the askfile path from JavaScript (download_dir result)
	# or the directory for multivolume/folder files
	return run_async(download_async(file, directory, directory))

async def download_async(file, directory, askfile=None):
	"""Async версия скачивания файлов"""
	global current_file_size, archiver
	PATH = read_path()

	with open('path.bd', 'r', encoding = 'utf-8') as file_:
		F = file_.readlines()

	idx = path_index(file, PATH)
	if idx is None:
		print("⚠️ download: путь не найден в path.bd: " + str(file))
		return False
	temp = json.loads(F[idx])[1]
	
	# Check if this is a multivolume file
	if isinstance(temp, dict) and temp.get('is_multivolume'):
		print(f"📦 Обнаружен многотомный архив: {temp['original_name']}")
		print(f"   Томов: {temp['total_volumes']}, Размер: {format_file_size(temp['original_size'])}")
		
		is_folder = temp.get('is_folder', False)
		
		if not archiver:
			print("❌ 7-Zip не найден! Установите 7-Zip для распаковки многотомных архивов.")
			return False
		
		temp_dir = None
		extract_dir = None
		
		try:
			# Create temporary directory for volumes
			temp_dir = get_temp_dir(prefix="tgdrive_download_")
			
			# ✅ ИЗМЕНЕНИЕ: Последовательное скачивание томов (Pyrogram ограничение)
			volumes = temp['volumes']
			print(f"📥 Скачивание {len(volumes)} томов...")
			
			volume_paths = []
			for vol in volumes:
				vol_num = vol['volume_number']
				print(f"📥 Скачивание тома {vol_num}/{temp['total_volumes']}...")
				
				# ✅ ИСПРАВЛЕНИЕ: Получаем свежий file_id из сообщения
				try:
					message = await app.get_messages('TelegCloudyBot', vol['message_id'])
					fresh_file_id = message.document.file_id
					file_size = vol['file_size']
				except Exception as e:
					print(f"⚠️ Не удалось получить свежий file_id для тома {vol_num}, используем старый: {e}")
					fresh_file_id = vol['file_id']
					file_size = vol['file_size']
				
				# Download volume with optimization
				vol_path = os.path.join(temp_dir, f"{temp['original_name']}.7z.{vol_num:03d}")
				
				# ✅ ОПТИМИЗАЦИЯ: Используем оптимизированное скачивание
				await optimizer.download_with_retry(
					app,
					fresh_file_id,
					vol_path,
					progress_callback=lambda c, t, s, stats: progress2(c, t, file_size),
					use_adaptive_chunking=True,
					max_retries=5
				)
				
				print(f"✅ Том {vol_num}/{temp['total_volumes']} скачан")
				volume_paths.append(vol_path)
			
			print("📦 Распаковка архива...")
			
			# ✅ ИЗМЕНЕНИЕ: Распаковка асинхронно
			extract_dir = get_temp_dir(prefix="tgdrive_extract_")
			success = await run_in_executor(archiver.extract_archive, volume_paths[0], extract_dir)
			
			if not success:
				print("❌ Ошибка распаковки архива")
				return False
			
			# Check if we got a .7z file that needs second extraction
			extracted_items = os.listdir(extract_dir)
			print(f"🔍 Найдено элементов после распаковки: {len(extracted_items)}")
			for item in extracted_items:
				print(f"   - {item}")
			
			# If we got a single .7z file, extract it again
			if len(extracted_items) == 1 and extracted_items[0].endswith('.7z'):
				print("📦 Обнаружен вложенный архив, распаковка...")
				nested_archive = os.path.join(extract_dir, extracted_items[0])
				nested_extract_dir = get_temp_dir(prefix="tgdrive_nested_")
				
				success = await run_in_executor(archiver.extract_archive, nested_archive, nested_extract_dir)
				if not success:
					print("❌ Ошибка распаковки вложенного архива")
					return False
				
				# Replace extract_dir with nested extraction
				await run_in_executor(shutil.rmtree, extract_dir)
				extract_dir = nested_extract_dir
				extracted_items = os.listdir(extract_dir)
				print(f"🔍 После второй распаковки найдено: {len(extracted_items)}")
				for item in extracted_items:
					print(f"   - {item}")
			
			if extracted_items:
				if is_folder:
					# It's a folder - handle properly
					folder_name = temp['original_name']
					
					if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
						# Single folder extracted - move it directly to destination
						extracted_item = os.path.join(extract_dir, extracted_items[0])
						destination_path = os.path.join(directory, extracted_items[0])
						print(f"📂 Перемещение папки: {extracted_item} -> {destination_path}")
						await run_in_executor(shutil.move, extracted_item, destination_path)
					else:
						# Multiple files/folders - create destination folder and move all
						destination_path = os.path.join(directory, folder_name)
						os.makedirs(destination_path, exist_ok=True)
						print(f"📂 Создание папки и перемещение содержимого: {destination_path}")
						
						# ✅ ИЗМЕНЕНИЕ: Параллельное перемещение файлов
						move_tasks = []
						for item in extracted_items:
							src = os.path.join(extract_dir, item)
							dst = os.path.join(destination_path, item)
							move_tasks.append(run_in_executor(shutil.move, src, dst))
						await asyncio.gather(*move_tasks)
					
					print(f"✅ Папка успешно скачана и распакована: {folder_name}")
				else:
					# It's a file
					extracted_file = os.path.join(extract_dir, extracted_items[0])
					await run_in_executor(shutil.move, extracted_file, directory)
					print(f"✅ Файл успешно скачан и распакован: {temp['original_name']}")
				return True
			else:
				print("❌ Не найдены распакованные файлы")
				return False
		
		except Exception as e:
			print(f"❌ Ошибка скачивания многотомного файла: {e}")
			return False
		
		finally:
			# Cleanup
			if temp_dir and os.path.exists(temp_dir):
				try:
					await run_in_executor(shutil.rmtree, temp_dir)
				except:
					pass
			if extract_dir and os.path.exists(extract_dir):
				try:
					await run_in_executor(shutil.rmtree, extract_dir)
				except:
					pass
	
	else:
		# Check if it's a folder archive (single file)
		is_folder = temp.get('is_folder', False)
		
		if is_folder and archiver:
			# Download and extract folder archive
			temp_dir = None
			extract_dir = None
			
			try:
				# Download archive to temp
				temp_dir = get_temp_dir(prefix="tgdrive_download_")
				archive_path = os.path.join(temp_dir, f"{file.split('/')[-1]}.7z")
				
				# ✅ ИСПРАВЛЕНИЕ: Получаем свежий file_id из сообщения
				try:
					message = await app.get_messages('TelegCloudyBot', temp['message_id'])
					file_id = message.document.file_id
					file_size = temp['file_size']
				except Exception as e:
					print(f"⚠️ Не удалось получить свежий file_id, используем старый: {e}")
					file_id = temp['file_id']
					file_size = temp['file_size']
				
				print(f"📥 Скачивание архива папки...")
				
				# ✅ ОПТИМИЗАЦИЯ: Используем оптимизированное скачивание
				await optimizer.download_with_retry(
					app,
					file_id,
					archive_path,
					progress_callback=lambda c, t, s, stats: progress2(c, t, file_size),
					use_adaptive_chunking=True,
					max_retries=5
				)
				
				print("📦 Распаковка папки...")
				extract_dir = get_temp_dir(prefix="tgdrive_extract_")
				success = await run_in_executor(archiver.extract_archive, archive_path, extract_dir)
				
				if not success:
					print("❌ Ошибка распаковки папки")
					return False
				
				# Move extracted folder to destination
				extracted_items = os.listdir(extract_dir)
				print(f"🔍 Найдено элементов после распаковки: {len(extracted_items)}")
				for item in extracted_items:
					print(f"   - {item}")
				
				if extracted_items:
					# Get folder name from file path
					folder_name = file.split('/')[-1]
					
					if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
						# Single folder extracted - move it directly to destination
						extracted_folder = os.path.join(extract_dir, extracted_items[0])
						destination_path = os.path.join(directory, extracted_items[0])
						print(f"📂 Перемещение папки: {extracted_folder} -> {destination_path}")
						await run_in_executor(shutil.move, extracted_folder, destination_path)
					else:
						# Multiple files/folders - create destination folder and move all
						destination_path = os.path.join(directory, folder_name)
						os.makedirs(destination_path, exist_ok=True)
						print(f"📂 Создание папки и перемещение содержимого: {destination_path}")
						
						move_tasks = []
						for item in extracted_items:
							src = os.path.join(extract_dir, item)
							dst = os.path.join(destination_path, item)
							move_tasks.append(run_in_executor(shutil.move, src, dst))
						await asyncio.gather(*move_tasks)
					
					print(f"✅ Папка успешно скачана и распакована: {folder_name}")
					return True
				else:
					print("❌ Не найдены распакованные файлы")
					return False
					
			except Exception as e:
				print(f"❌ Ошибка скачивания папки: {e}")
				return False
				
			finally:
				# Cleanup
				if temp_dir and os.path.exists(temp_dir):
					try:
						await run_in_executor(shutil.rmtree, temp_dir)
					except:
						pass
				if extract_dir and os.path.exists(extract_dir):
					try:
						await run_in_executor(shutil.rmtree, extract_dir)
					except:
						pass
		else:
			# Normal single file download
			# ✅ ИСПРАВЛЕНИЕ: Получаем свежий file_id из сообщения
			try:
				message = await app.get_messages('TelegCloudyBot', temp['message_id'])
				file_id = message.document.file_id
				file_size = temp['file_size']
			except Exception as e:
				print(f"⚠️ Не удалось получить свежий file_id, используем старый: {e}")
				file_id = temp['file_id']
				file_size = temp['file_size']
			
			# Use the askfile path passed from sync wrapper
			if askfile:
				# ✅ ОПТИМИЗАЦИЯ: Используем оптимизированное скачивание
				await optimizer.download_with_retry(
					app,
					file_id,
					askfile,
					progress_callback=lambda c, t, s, stats: progress2(c, t, file_size),
					use_adaptive_chunking=True,
					max_retries=5
				)
				return True
			return False

@eel.expose
def opendir(dir_):
	arr = dir_.split("/")
	str_ = ""
	for i in range(len(arr)):
		if i != len(arr)-1:
			str_ += arr[i] + "\\"
		else:
			str_ += arr[i]
	os.system(f'explorer /select, "{str_}"')


def size_str(bytes_size):
	if bytes_size > 1000000000:
		return str(round(bytes_size/1073741824, 2)) + LANGUAGES[global_lang]["python"]["GB"]
	elif bytes_size > 399999:
		return str(round(bytes_size/1048576, 2)) + LANGUAGES[global_lang]["python"]["MB"]
	elif bytes_size > 999:
		return str(int(bytes_size/1024)) + LANGUAGES[global_lang]["python"]["KB"]
	else:
		return str(bytes_size) + LANGUAGES[global_lang]["python"]["bites"]

@eel.expose
def file_size(file):
	PATH = read_path()
	with open('path.bd', 'r', encoding = 'utf-8') as file_:
		F = file_.readlines()

	temp = json.loads(F[PATH.index(file)])[1]
	
	# Check if multivolume
	if isinstance(temp, dict) and temp.get('is_multivolume'):
		folder_icon = " 📁" if temp.get('is_folder', False) else ""
		return size_str(temp['original_size']) + " 📦" + folder_icon
	elif isinstance(temp, dict) and temp.get('is_folder', False):
		return size_str(temp['file_size']) + " 📁"
	else:
		return size_str(temp['file_size'])

@eel.expose
def search(text):
	PATH = read_path()
	array = {"files":[], "folders":[]}
	text = text.lower()
	if PATH:
		for i in PATH:
			if text in i.lower():
				temp = i.split("/")
				if len(temp[-1]) > 0:
					if text in temp[-1].lower():
						array["files"].append(i)
				else:
					if text in temp[-2].lower():
						array["folders"].append(i)
	return array

@eel.expose
def sort_this(array):
	folders = []
	files = []
	for i in array:
		if i[0] == "file":
			files.append(i)
		if i[0] == "folder":
			folders.append(i)

	if current_sort == "by_alphabet":
		folders = sorted(folders)
		files = sorted(files)
		for i in files:
			folders.append(i)
		return folders
	if current_sort == "by_alphabet_reverse":
		folders = sorted(folders)
		folders.reverse()
		files = sorted(files)
		files.reverse()
		for i in files:
			folders.append(i)
		return folders
	if current_sort == "by_date":
		for i in files:
			folders.append(i)
		return folders
	if current_sort == "by_date_reverse":
		folders.reverse()
		files.reverse()
		for i in files:
			folders.append(i)
		return folders

@eel.expose
def show_preview(file):
	if preview_only_images:
		index = file.split(".")[-1]
		for i in file_types:
			for x in i:
				if x == index:
					type_of_file = file_types_str[file_types.index(i)]
					break
		if type_of_file != "image":
			return

	PATH = read_path()
	with open('path.bd', 'r', encoding = 'utf-8') as file_:
		F = file_.readlines()

	temp = json.loads(F[PATH.index(file)])[1]
	try:
		msg_pre_id = temp['preview_file_id']
		app.download_media(msg_pre_id, file_name="Web\\Temp\\file_preview."+file.split(".")[-1])
		return "Temp\\file_preview."+file.split(".")[-1]
	except:
		return

@eel.expose
def delete_preview():
	try:
		shutil.rmtree("Web\\Temp\\")
	except:
		None

@eel.expose
def memory_used():
	full_size = 0
	try:
		with open('path.bd', 'r', encoding = 'utf-8') as file_:
			F = file_.readlines()
		for i in F:
			try:
				data = json.loads(i)[1]
				# Check if it's a multivolume archive
				if isinstance(data, dict) and data.get('is_multivolume'):
					# Use original_size for multivolume archives
					full_size += data.get('original_size', 0)
				elif isinstance(data, dict):
					# Regular dict entry (might be folder or single file)
					full_size += data.get('file_size', 0)
				else:
					# Old format: just file_size
					full_size += data.get('file_size', 0) if isinstance(data, dict) else 0
			except:
				None
	except FileNotFoundError:
		None
	return size_str(full_size)


eel.init(resource_path("Web"))

if os.path.exists(executable_path()+'\\config.ini'):
	if not os.path.exists(resource_path("")+'config.ini'):
		shutil.copy(executable_path()+'\\config.ini', resource_path(""))
	if not os.path.exists(resource_path("")+'TelegramCloud.session'):
		shutil.copy(executable_path()+'\\TelegramCloud.session', resource_path(""))
	if not os.path.exists(resource_path("")+'path.bd'):
		try:
			shutil.copy(executable_path()+'\\path.bd', resource_path(""))
		except:
			None
	if not os.path.exists(resource_path("")+'settings.json'):
		try:
			shutil.copy(executable_path()+'\\settings.json', resource_path(""))
		except:
			None


	if check_theme() == "dark":
		eel.start("dark.html")
	else:
		eel.start("main.html")
else:
	eel.start("login.html")
