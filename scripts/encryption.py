"""
Модуль шифрования для TG Drive RE
Обеспечивает end-to-end шифрование файлов перед загрузкой в Telegram
"""

import os
import base64
import json
from typing import Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """Менеджер шифрования файлов"""
    
    def __init__(self):
        self.key = None
        self.cipher = None
        self.salt = None
    
    def generate_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """
        Генерация ключа шифрования из пароля пользователя
        
        Args:
            password: мастер-пароль пользователя
            salt: соль для генерации ключа (если None, создается новая)
        
        Returns:
            salt: соль для сохранения
        """
        if salt is None:
            salt = os.urandom(16)
        
        self.salt = salt
        
        # Генерация ключа с использованием PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.key = key
        self.cipher = Fernet(key)
        
        return salt
    
    def is_initialized(self) -> bool:
        """Проверка инициализации шифрования"""
        return self.cipher is not None
    
    def encrypt_file(self, file_path: str, output_path: str = None) -> str:
        """
        Шифрование файла перед загрузкой
        
        Args:
            file_path: путь к исходному файлу
            output_path: путь для сохранения зашифрованного файла
        
        Returns:
            путь к зашифрованному файлу
        """
        if not self.cipher:
            raise Exception("Шифрование не инициализировано! Установите пароль.")
        
        # Чтение файла
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Шифрование
        encrypted_data = self.cipher.encrypt(data)
        
        # Определение пути для сохранения
        if output_path is None:
            output_path = file_path + '.encrypted'
        
        # Сохранение зашифрованного файла
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        return output_path
    
    def decrypt_file(self, encrypted_path: str, output_path: str) -> bool:
        """
        Расшифровка файла после скачивания
        
        Args:
            encrypted_path: путь к зашифрованному файлу
            output_path: путь для сохранения расшифрованного файла
        
        Returns:
            True если успешно, False если ошибка
        """
        if not self.cipher:
            raise Exception("Шифрование не инициализировано! Установите пароль.")
        
        try:
            # Чтение зашифрованного файла
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Расшифровка
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Сохранение расшифрованного файла
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return True
            
        except Exception as e:
            print(f"Ошибка расшифровки: {e}")
            return False
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Шифрование данных в памяти"""
        if not self.cipher:
            raise Exception("Шифрование не инициализировано!")
        return self.cipher.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Расшифровка данных в памяти"""
        if not self.cipher:
            raise Exception("Шифрование не инициализировано!")
        return self.cipher.decrypt(encrypted_data)
    
    def save_salt(self, settings_file='settings.json'):
        """Сохранение соли в настройках"""
        if not self.salt:
            return
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.loads(f.read())
        except FileNotFoundError:
            settings = {}
        
        settings['encryption_enabled'] = True
        settings['encryption_salt'] = base64.b64encode(self.salt).decode('utf-8')
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(settings, ensure_ascii=False, indent=2))
    
    def load_salt(self, settings_file='settings.json') -> Optional[bytes]:
        """Загрузка соли из настроек"""
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.loads(f.read())
            
            if settings.get('encryption_enabled') and settings.get('encryption_salt'):
                salt = base64.b64decode(settings['encryption_salt'])
                self.salt = salt
                return salt
            
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            pass
        
        return None
    
    def is_encryption_enabled(self, settings_file='settings.json') -> bool:
        """Проверка включено ли шифрование в настройках"""
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.loads(f.read())
            return settings.get('encryption_enabled', False)
        except:
            return False
    
    def disable_encryption(self, settings_file='settings.json'):
        """Отключение шифрования"""
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.loads(f.read())
        except FileNotFoundError:
            settings = {}
        
        settings['encryption_enabled'] = False
        if 'encryption_salt' in settings:
            del settings['encryption_salt']
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(settings, ensure_ascii=False, indent=2))
        
        # Очистка ключей из памяти
        self.key = None
        self.cipher = None
        self.salt = None


def test_encryption():
    """Тест функций шифрования"""
    print("🔐 Тест модуля шифрования...")
    
    # Создание тестового файла
    test_file = "test_encryption.txt"
    test_data = "Это секретные данные для тестирования шифрования! 🔒"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_data)
    
    # Инициализация менеджера
    em = EncryptionManager()
    password = "test_password_123"
    
    # Генерация ключа
    salt = em.generate_key_from_password(password)
    print(f"✅ Ключ сгенерирован (соль: {len(salt)} байт)")
    
    # Шифрование
    encrypted_file = em.encrypt_file(test_file)
    print(f"✅ Файл зашифрован: {encrypted_file}")
    
    # Расшифровка
    decrypted_file = "test_decrypted.txt"
    success = em.decrypt_file(encrypted_file, decrypted_file)
    
    if success:
        with open(decrypted_file, 'r', encoding='utf-8') as f:
            decrypted_data = f.read()
        
        if decrypted_data == test_data:
            print("✅ Расшифровка успешна! Данные совпадают.")
        else:
            print("❌ Ошибка: данные не совпадают!")
    else:
        print("❌ Ошибка расшифровки!")
    
    # Очистка
    os.remove(test_file)
    os.remove(encrypted_file)
    os.remove(decrypted_file)
    
    print("✅ Тест завершен!")


if __name__ == "__main__":
    test_encryption()
