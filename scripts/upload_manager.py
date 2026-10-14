"""
Улучшенный модуль загрузки с поддержкой шифрования и больших файлов
TG Drive RE - Enhanced Upload Module with Optimized Uploading and Premium Support
"""

import os
import tempfile
import shutil
import asyncio
from typing import List, Dict, Optional, Callable
from pathlib import Path
from database import DatabaseManager
from encryption import EncryptionManager
from archiver import MultiVolumeArchiver, SevenZipManager
from optimized_uploader import OptimizedUploader, create_optimized_uploader
from premium_detector import PremiumDetector, get_premium_detector


class UploadManager:
    """Менеджер загрузки файлов с поддержкой шифрования и разбиения"""
    
    def __init__(self, app, db: DatabaseManager, 
                 encryption: Optional[EncryptionManager] = None,
                 archiver: Optional[MultiVolumeArchiver] = None,
                 use_optimized_upload: bool = True,
                 premium_detector: Optional[PremiumDetector] = None,
                 custom_temp_folder: Optional[str] = None):
        self.app = app
        self.db = db
        self.encryption = encryption
        self.archiver = archiver
        self.stop_transmit = False
        self.use_optimized_upload = use_optimized_upload
        self.optimized_uploader: Optional[OptimizedUploader] = None
        self.premium_detector = premium_detector or get_premium_detector()
        self.custom_temp_folder = custom_temp_folder
        
    async def initialize_optimized_uploader(self, telethon_client=None):
        """Initialize optimized uploader with Telethon client"""
        if self.use_optimized_upload and telethon_client:
            self.optimized_uploader = await create_optimized_uploader(
                telethon_client,
                auto_select_dc=True
            )
    
    def _get_temp_dir(self, prefix: str = "tgdrive_") -> str:
        """Get temporary directory path (custom or system default)"""
        if self.custom_temp_folder and os.path.exists(self.custom_temp_folder):
            temp_path = os.path.join(self.custom_temp_folder, prefix + os.urandom(8).hex())
            os.makedirs(temp_path, exist_ok=True)
            return temp_path
        else:
            return tempfile.mkdtemp(prefix=prefix)
    
    def detect_premium(self, pyrogram_app=None, telethon_client=None, manual: Optional[bool] = None):
        """
        Определить Premium статус и обновить лимиты
        
        Args:
            pyrogram_app: Pyrogram client для автоопределения
            telethon_client: Telethon client для автоопределения
            manual: Ручная установка (True/False/None для авто)
        """
        is_premium = False
        
        if manual is not None:
            # Ручная установка
            self.premium_detector.set_premium_manual(manual)
            is_premium = manual
        elif pyrogram_app:
            # Автоопределение через Pyrogram
            is_premium = self.premium_detector.detect_premium_pyrogram(pyrogram_app)
        elif telethon_client:
            # Автоопределение через Telethon
            import asyncio
            loop = asyncio.get_event_loop()
            is_premium = loop.run_until_complete(
                self.premium_detector.detect_premium_telethon(telethon_client)
            )
        
        # Обновить лимиты в archiver
        if self.archiver:
            self.archiver.set_premium_mode(is_premium)
        
        return is_premium
    
    def upload_file(self, file_path: str, telegram_path: str, 
                   encrypt: bool = False,
                   compress_if_large: bool = True,
                   progress_callback: Optional[Callable] = None,
                   use_optimization: bool = True) -> Dict:
        """
        Загрузка одного файла с опциональным шифрованием
        
        Args:
            file_path: путь к локальному файлу
            telegram_path: путь в Telegram Cloud
            encrypt: шифровать ли файл перед загрузкой
            compress_if_large: разбивать ли большие файлы на тома
            progress_callback: функция для отслеживания прогресса
            use_optimization: использовать оптимизированную загрузку
        
        Returns:
            dict с результатом загрузки
        """
        result = {
            'success': False,
            'path': telegram_path,
            'encrypted': False,
            'multivolume': False,
            'error': None
        }
        
        temp_files = []
        
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Проверка существования
            if self.db.get_file(telegram_path):
                result['error'] = 'File already exists'
                return result
            
            # Шифрование (если требуется)
            upload_path = file_path
            if encrypt:
                if not self.encryption or not self.encryption.is_initialized():
                    result['error'] = 'Encryption not initialized'
                    return result
                
                print(f"🔐 Шифрование файла: {file_name}")
                encrypted_path = file_path + '.encrypted'
                self.encryption.encrypt_file(file_path, encrypted_path)
                upload_path = encrypted_path
                temp_files.append(encrypted_path)
                result['encrypted'] = True
            
            # Проверка размера и разбиение (если требуется)
            if compress_if_large and self.archiver and self.archiver.needs_splitting(upload_path):
                result['multivolume'] = True
                return self._upload_multivolume(
                    upload_path, telegram_path, file_name, 
                    file_size, encrypt, progress_callback
                )
            
            # Обычная загрузка
            print(f"📤 Загрузка: {file_name} ({self._format_size(file_size)})")
            
            # Использовать оптимизированную загрузку если доступна
            if use_optimization and self.optimized_uploader:
                print("⚡ Использование оптимизированной загрузки (Multi-DC + Adaptive)")
                
                # Async wrapper для оптимизированной загрузки
                # Note: Requires Telethon client, falls back to Pyrogram if not available
                try:
                    async def optimized_upload():
                        # Get chat entity for TelegCloudyBot
                        chat = await self.optimized_uploader.client.get_entity('TelegCloudyBot')
                        return await self.optimized_uploader.upload_file(
                            Path(upload_path),
                            chat_id=chat.id,
                            caption="",
                            progress_callback=progress_callback,
                            use_adaptive_chunking=True
                        )
                    
                    # Запуск в event loop
                    loop = asyncio.get_event_loop()
                    message = loop.run_until_complete(optimized_upload())
                except Exception as opt_error:
                    print(f"⚠️ Оптимизированная загрузка недоступна: {opt_error}")
                    print("   Использование стандартной загрузки...")
                    with open(upload_path, 'rb') as f:
                        message = self.app.send_document(
                            'TelegCloudyBot', 
                            f,
                            progress=progress_callback
                        )
            else:
                # Обычная загрузка через Pyrogram
                with open(upload_path, 'rb') as f:
                    message = self.app.send_document(
                        'TelegCloudyBot', 
                        f,
                        progress=progress_callback
                    )
            
            # Сохранение в БД
            parent_path = os.path.dirname(telegram_path) + '/'
            extension = os.path.splitext(file_name)[1].lstrip('.')
            
            self.db.add_file(
                path=telegram_path,
                name=file_name,
                parent_path=parent_path,
                is_folder=False,
                file_id=message.document.file_id,
                message_id=message.message_id,
                file_size=message.document.file_size,
                extension=extension,
                is_encrypted=encrypt
            )
            
            result['success'] = True
            print(f"✅ Загружено: {file_name}")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Ошибка загрузки: {e}")
        
        finally:
            # Очистка временных файлов
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        return result
    
    def _upload_multivolume(self, file_path: str, telegram_path: str,
                           file_name: str, original_size: int,
                           is_encrypted: bool,
                           progress_callback: Optional[Callable]) -> Dict:
        """Загрузка большого файла с разбиением на тома"""
        
        result = {
            'success': False,
            'path': telegram_path,
            'encrypted': is_encrypted,
            'multivolume': True,
            'error': None
        }
        
        temp_dir = None
        
        try:
            if not self.archiver:
                result['error'] = 'Archiver not initialized'
                return result
            
            print(f"📦 Создание многотомного архива для: {file_name}")
            
            # Создание архива
            volumes, temp_dir = self.archiver.create_archive(
                file_path,
                progress_callback=progress_callback
            )
            
            print(f"📤 Загрузка {len(volumes)} томов...")
            
            # Загрузка томов
            volume_metadata = []
            for i, volume_path in enumerate(volumes, 1):
                print(f"   Том {i}/{len(volumes)}: {os.path.basename(volume_path)}")
                
                with open(volume_path, 'rb') as f:
                    msg = self.app.send_document(
                        'TelegCloudyBot',
                        f,
                        caption=f"Volume {i}/{len(volumes)}",
                        progress=progress_callback
                    )
                
                volume_metadata.append({
                    'volume_number': i,
                    'message_id': msg.message_id,
                    'file_id_telegram': msg.document.file_id,
                    'file_size': msg.document.file_size
                })
            
            # Сохранение в БД
            parent_path = os.path.dirname(telegram_path) + '/'
            extension = os.path.splitext(file_name)[1].lstrip('.')
            
            total_compressed_size = sum(v['file_size'] for v in volume_metadata)
            compression_ratio = total_compressed_size / original_size if original_size > 0 else 1.0
            
            file_id = self.db.add_file(
                path=telegram_path,
                name=file_name,
                parent_path=parent_path,
                is_folder=False,
                is_multivolume=True,
                original_size=original_size,
                compression_ratio=compression_ratio,
                extension=extension,
                is_encrypted=is_encrypted
            )
            
            # Сохранение томов
            for vol in volume_metadata:
                self.db.add_volume(file_id, vol)
            
            result['success'] = True
            print(f"✅ Загружено {len(volumes)} томов")
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Ошибка загрузки многотомного файла: {e}")
        
        finally:
            # Очистка
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        
        return result
    
    def upload_batch(self, file_paths: List[str], telegram_dir: str,
                    encrypt: bool = False,
                    compress_if_large: bool = True,
                    progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Пакетная загрузка файлов
        
        Args:
            file_paths: список путей к файлам
            telegram_dir: директория в Telegram Cloud
            encrypt: шифровать ли файлы
            compress_if_large: разбивать ли большие файлы
            progress_callback: функция для отслеживания прогресса
        
        Returns:
            список результатов для каждого файла
        """
        results = []
        
        for i, file_path in enumerate(file_paths, 1):
            if self.stop_transmit:
                break
            
            file_name = os.path.basename(file_path)
            telegram_path = telegram_dir + file_name
            
            print(f"\n[{i}/{len(file_paths)}] {file_name}")
            
            result = self.upload_file(
                file_path,
                telegram_path,
                encrypt=encrypt,
                compress_if_large=compress_if_large,
                progress_callback=progress_callback
            )
            
            results.append(result)
        
        return results
    
    def _format_size(self, bytes_size: int) -> str:
        """Форматирование размера"""
        size_float = float(bytes_size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024.0:
                return f"{size_float:.2f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.2f} PB"


class DownloadManager:
    """Менеджер скачивания файлов с поддержкой расшифровки"""
    
    def __init__(self, app, db: DatabaseManager,
                 encryption: Optional[EncryptionManager] = None,
                 archiver: Optional[MultiVolumeArchiver] = None):
        self.app = app
        self.db = db
        self.encryption = encryption
        self.archiver = archiver
    
    def download_file(self, telegram_path: str, local_path: str,
                     progress_callback: Optional[Callable] = None) -> bool:
        """
        Скачивание файла с автоматической расшифровкой
        
        Args:
            telegram_path: путь в Telegram Cloud
            local_path: куда сохранить файл
            progress_callback: функция для отслеживания прогресса
        
        Returns:
            True если успешно
        """
        try:
            file_info = self.db.get_file(telegram_path)
            
            if not file_info:
                print(f"❌ Файл не найден: {telegram_path}")
                return False
            
            # Многотомный архив
            if file_info['is_multivolume']:
                return self._download_multivolume(file_info, local_path, progress_callback)
            
            # Обычный файл
            print(f"📥 Скачивание: {file_info['name']}")
            
            # Скачивание
            temp_path = local_path
            if file_info['is_encrypted']:
                temp_path = local_path + '.encrypted'
            
            self.app.download_media(
                file_info['file_id'],
                file_name=temp_path,
                progress=progress_callback
            )
            
            # Расшифровка (если требуется)
            if file_info['is_encrypted']:
                if not self.encryption or not self.encryption.is_initialized():
                    print("❌ Шифрование не инициализировано!")
                    return False
                
                print("🔓 Расшифровка файла...")
                success = self.encryption.decrypt_file(temp_path, local_path)
                
                # Удаление зашифрованного файла
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                if not success:
                    return False
            
            print(f"✅ Скачано: {file_info['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка скачивания: {e}")
            return False
    
    def _download_multivolume(self, file_info: Dict, local_path: str,
                             progress_callback: Optional[Callable]) -> bool:
        """Скачивание и распаковка многотомного архива"""
        
        temp_dir = None
        
        try:
            if not self.archiver:
                print("❌ Archiver not initialized")
                return False
            
            volumes = self.db.get_volumes(file_info['id'])
            
            if not volumes:
                print("❌ Тома не найдены")
                return False
            
            print(f"📥 Скачивание {len(volumes)} томов...")
            
            # Временная директория
            temp_dir = self._get_temp_dir(prefix="tgdrive_download_")
            
            # Скачивание томов
            volume_paths = []
            for i, vol in enumerate(volumes, 1):
                print(f"   Том {i}/{len(volumes)}")
                
                volume_path = os.path.join(temp_dir, f"volume.7z.{i:03d}")
                
                self.app.download_media(
                    vol['file_id_telegram'],
                    file_name=volume_path,
                    progress=progress_callback
                )
                
                volume_paths.append(volume_path)
            
            # Распаковка
            print("📦 Распаковка архива...")
            extract_dir = self._get_temp_dir(prefix="tgdrive_extract_")
            
            success = self.archiver.extract_archive(
                volume_paths[0],
                extract_dir,
                progress_callback=progress_callback
            )
            
            if not success:
                return False
            
            # Перемещение файла
            extracted_files = os.listdir(extract_dir)
            if extracted_files:
                extracted_file = os.path.join(extract_dir, extracted_files[0])
                shutil.move(extracted_file, local_path)
            
            # Расшифровка (если требуется)
            if file_info['is_encrypted']:
                if not self.encryption or not self.encryption.is_initialized():
                    print("❌ Шифрование не инициализировано!")
                    return False
                
                print("🔓 Расшифровка файла...")
                temp_encrypted = local_path + '.encrypted'
                shutil.move(local_path, temp_encrypted)
                
                success = self.encryption.decrypt_file(temp_encrypted, local_path)
                os.remove(temp_encrypted)
                
                if not success:
                    return False
            
            print(f"✅ Скачано и распаковано: {file_info['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка скачивания многотомного файла: {e}")
            return False
        
        finally:
            # Очистка
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
