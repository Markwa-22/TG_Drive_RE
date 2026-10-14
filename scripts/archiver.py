"""
Модуль для работы с 7-Zip и многотомными архивами
TG Drive RE - 7-Zip Integration & Multi-Volume Support
"""

import subprocess
import os
import platform
import tempfile
import shutil
import threading
import time
from typing import List, Optional, Tuple, Callable
from pathlib import Path


class SevenZipManager:
    """Менеджер для работы с 7-Zip"""
    
    def __init__(self):
        self.seven_zip_path = self.find_7zip()
        if not self.seven_zip_path:
            raise Exception("7-Zip не найден! Установите 7-Zip: https://www.7-zip.org/")
    
    def find_7zip(self) -> Optional[str]:
        """Поиск 7z.exe в системе"""
        # Возможные пути
        possible_paths = [
            "7z",  # В PATH
            "C:\\Program Files\\7-Zip\\7z.exe",
            "C:\\Program Files (x86)\\7-Zip\\7z.exe",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "7z.exe"),  # Bundled (tools/ рядом с main.py)
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path], 
                    capture_output=True, 
                    timeout=2
                )
                # 7z возвращает 0 или 7 при успешном запуске без аргументов
                if result.returncode in [0, 7]:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def get_version(self) -> str:
        """Получить версию 7-Zip"""
        try:
            result = subprocess.run(
                [self.seven_zip_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Парсить вывод для версии
            for line in result.stdout.split('\n'):
                if '7-Zip' in line:
                    return line.strip()
            return "Unknown"
        except:
            return "Unknown"
    
    def test_archive(self, archive_path: str) -> bool:
        """Проверка целостности архива"""
        try:
            cmd = [
                self.seven_zip_path,
                "t",  # Test
                archive_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except:
            return False


class MultiVolumeArchiver:
    """Менеджер многотомных архивов для больших файлов"""
    
    # Default limits (Standard Telegram)
    TELEGRAM_LIMIT_STANDARD = 2 * 1024 * 1024 * 1024  # 2 GB
    SPLIT_THRESHOLD_STANDARD = 1.9 * 1024 * 1024 * 1024  # 1.9 GB (запас)
    VOLUME_SIZE_STANDARD = "1900m"  # Размер тома
    
    # Premium limits (Telegram Premium)
    TELEGRAM_LIMIT_PREMIUM = 4 * 1024 * 1024 * 1024  # 4 GB
    SPLIT_THRESHOLD_PREMIUM = 3.9 * 1024 * 1024 * 1024  # 3.9 GB (запас)
    VOLUME_SIZE_PREMIUM = "3900m"  # Размер тома для Premium
    
    # Расширения уже сжатых файлов (не нужно сжимать повторно)
    NO_COMPRESS_EXT = {
        '.zip', '.rar', '.7z', '.gz', '.bz2', '.xz', '.tar',  # Архивы
        '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp',  # Изображения
        '.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv',  # Видео
        '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma',  # Аудио
        '.pdf', '.doc', '.docx', '.ppt', '.pptx',  # Документы (часто сжаты)
    }
    
    def __init__(self, seven_zip_manager: SevenZipManager, is_premium: bool = False, custom_temp_folder: Optional[str] = None):
        self.sz = seven_zip_manager
        self.is_premium = is_premium
        self.custom_temp_folder = custom_temp_folder
        self._update_limits()
    
    def _update_limits(self):
        """Обновить лимиты в зависимости от Premium статуса"""
        if self.is_premium:
            self.telegram_limit = self.TELEGRAM_LIMIT_PREMIUM
            self.split_threshold = self.SPLIT_THRESHOLD_PREMIUM
            self.volume_size = self.VOLUME_SIZE_PREMIUM
        else:
            self.telegram_limit = self.TELEGRAM_LIMIT_STANDARD
            self.split_threshold = self.SPLIT_THRESHOLD_STANDARD
            self.volume_size = self.VOLUME_SIZE_STANDARD
    
    def set_premium_mode(self, is_premium: bool):
        """
        Установить Premium режим
        
        Args:
            is_premium: True для Premium (4GB), False для Standard (2GB)
        """
        self.is_premium = is_premium
        self._update_limits()
        mode = "Premium (4GB)" if is_premium else "Standard (2GB)"
        print(f"📦 Archiver mode: {mode}")
    
    def needs_splitting(self, file_path: str) -> bool:
        """Проверка необходимости разбиения файла"""
        return os.path.getsize(file_path) > self.split_threshold
    
    def should_compress(self, file_path: str) -> bool:
        """Определить нужно ли сжимать файл"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext not in self.NO_COMPRESS_EXT
    
    def _get_temp_dir(self, prefix: str = "tgdrive_") -> str:
        """Get temporary directory path (custom or system default)"""
        if self.custom_temp_folder and os.path.exists(self.custom_temp_folder):
            temp_path = os.path.join(self.custom_temp_folder, prefix + os.urandom(8).hex())
            os.makedirs(temp_path, exist_ok=True)
            return temp_path
        else:
            return tempfile.mkdtemp(prefix=prefix)
    
    def create_archive(self, file_path: str, 
                      progress_callback: Optional[Callable] = None) -> Tuple[List[str], str]:
        """
        Создать многотомный архив
        
        Args:
            file_path: путь к файлу для архивации
            progress_callback: функция для отслеживания прогресса
        
        Returns:
            (список путей к томам, временная директория)
        """
        # Временная директория
        temp_dir = self._get_temp_dir(prefix="tgdrive_compress_")
        
        try:
            # Имя архива
            base_name = os.path.basename(file_path)
            archive_base = os.path.join(temp_dir, f"{base_name}.7z")
            
            # Определить уровень сжатия
            compression_level = "0" if not self.should_compress(file_path) else "5"
            
            # Команда 7-Zip
            cmd = [
                self.sz.seven_zip_path,
                "a",  # Добавить в архив
                f"-v{self.volume_size}",  # Размер тома
                f"-mx={compression_level}",  # Уровень сжатия (0=store, 5=normal, 9=ultra)
                "-mmt=on",  # Многопоточность
                "-bt",  # Показывать время выполнения
                archive_base,
                file_path
            ]
            
            print(f"🗜️  Создание архива: {base_name}")
            print(f"   Сжатие: {'Нет (копирование)' if compression_level == '0' else 'Да (уровень 5)'}")
            
            # Запуск с отслеживанием прогресса
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Мониторинг прогресса
            if progress_callback:
                monitor_thread = threading.Thread(
                    target=self._monitor_compression,
                    args=(process, temp_dir, progress_callback),
                    daemon=True
                )
                monitor_thread.start()
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Ошибка сжатия: {stderr}")
            
            # Найти все созданные тома
            volumes = []
            for file in sorted(os.listdir(temp_dir)):
                if file.startswith(base_name):
                    volumes.append(os.path.join(temp_dir, file))
            
            if not volumes:
                raise Exception("Не удалось создать тома архива")
            
            print(f"✅ Создано томов: {len(volumes)}")
            
            return volumes, temp_dir
            
        except Exception as e:
            # Очистка при ошибке
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
    
    def _monitor_compression(self, process, temp_dir, callback):
        """Мониторинг прогресса сжатия"""
        while process.poll() is None:
            try:
                # Подсчитать размер созданных томов
                current_size = sum(
                    os.path.getsize(os.path.join(temp_dir, f))
                    for f in os.listdir(temp_dir)
                    if os.path.isfile(os.path.join(temp_dir, f))
                )
                callback(current_size)
            except:
                pass
            time.sleep(0.5)
    
    def extract_archive(self, first_volume: str, output_dir: str,
                       progress_callback: Optional[Callable] = None) -> bool:
        """
        Распаковать многотомный архив
        
        Args:
            first_volume: путь к первому тому (.001 или .7z.001)
            output_dir: куда извлечь
            progress_callback: функция для отслеживания прогресса
        
        Returns:
            True если успешно
        """
        try:
            # Создать выходную директорию
            os.makedirs(output_dir, exist_ok=True)
            
            cmd = [
                self.sz.seven_zip_path,
                "x",  # Извлечь с путями
                f"-o{output_dir}",  # Выходная директория
                "-y",  # Yes на все вопросы
                "-bt",  # Показывать время
                first_volume
            ]
            
            print(f"📦 Распаковка архива: {os.path.basename(first_volume)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Мониторинг прогресса распаковки
            if progress_callback:
                for line in process.stdout:
                    if '%' in line:
                        # Парсить процент из вывода 7z
                        try:
                            percent = int(line.split('%')[0].strip().split()[-1])
                            progress_callback(percent)
                        except:
                            pass
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Ошибка распаковки: {stderr}")
            
            print("✅ Распаковка завершена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка распаковки: {e}")
            return False
    
    def verify_integrity(self, first_volume: str) -> bool:
        """Проверка целостности многотомного архива"""
        return self.sz.test_archive(first_volume)
    
    def get_archive_info(self, archive_path: str) -> dict:
        """Получить информацию об архиве"""
        try:
            cmd = [
                self.sz.seven_zip_path,
                "l",  # List
                "-slt",  # Technical info
                archive_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {}
            
            info = {
                'files': 0,
                'size': 0,
                'packed_size': 0
            }
            
            for line in result.stdout.split('\n'):
                if 'files' in line.lower():
                    try:
                        info['files'] = int(line.split(':')[1].strip())
                    except:
                        pass
                elif 'Size:' in line:
                    try:
                        info['size'] = int(line.split(':')[1].strip())
                    except:
                        pass
                elif 'Packed Size:' in line:
                    try:
                        info['packed_size'] = int(line.split(':')[1].strip())
                    except:
                        pass
            
            return info
            
        except:
            return {}


def format_size(bytes_size: int) -> str:
    """Форматирование размера в читаемый вид"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def test_7zip():
    """Тест функций 7-Zip"""
    print("🧪 Тест модуля 7-Zip...")
    
    try:
        # Инициализация
        sz = SevenZipManager()
        print(f"✅ 7-Zip найден: {sz.seven_zip_path}")
        print(f"   Версия: {sz.get_version()}")
        
        # Создание тестового файла
        test_file = "test_large_file.txt"
        with open(test_file, 'w') as f:
            f.write("Test data " * 1000000)  # ~10 MB
        
        file_size = os.path.getsize(test_file)
        print(f"✅ Создан тестовый файл: {format_size(file_size)}")
        
        # Создание архива
        archiver = MultiVolumeArchiver(sz)
        
        def progress(size):
            print(f"   Прогресс: {format_size(size)}", end='\r')
        
        volumes, temp_dir = archiver.create_archive(test_file, progress_callback=progress)
        print(f"\n✅ Создано томов: {len(volumes)}")
        
        for vol in volumes:
            print(f"   - {os.path.basename(vol)}: {format_size(os.path.getsize(vol))}")
        
        # Проверка целостности
        if archiver.verify_integrity(volumes[0]):
            print("✅ Проверка целостности пройдена")
        else:
            print("❌ Ошибка проверки целостности")
        
        # Распаковка
        extract_dir = archiver._get_temp_dir(prefix="tgdrive_extract_")
        success = archiver.extract_archive(volumes[0], extract_dir)
        
        if success:
            print("✅ Распаковка успешна")
        
        # Очистка
        os.remove(test_file)
        shutil.rmtree(temp_dir)
        shutil.rmtree(extract_dir)
        
        print("✅ Тест завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")


if __name__ == "__main__":
    test_7zip()
