"""
Скрипт миграции данных из path.bd в SQLite базу данных
TG Drive RE - Migration Tool
"""

import json
import shutil
import os
from database import DatabaseManager
from datetime import datetime


def migrate_from_pathbd(pathbd_file='path.bd', backup=True):
    """
    Миграция данных из старого формата path.bd в SQLite
    
    Args:
        pathbd_file: путь к файлу path.bd
        backup: создать ли резервную копию
    """
    
    print("=" * 60)
    print("TG Drive RE - Миграция в SQLite")
    print("=" * 60)
    
    # Проверка существования файла
    if not os.path.exists(pathbd_file):
        print(f"❌ Файл {pathbd_file} не найден!")
        print("✅ Создана новая пустая база данных SQLite")
        db = DatabaseManager()
        return
    
    # Создать бэкап
    if backup:
        backup_name = f"{pathbd_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy(pathbd_file, backup_name)
            print(f"✅ Создан бэкап: {backup_name}")
        except Exception as e:
            print(f"⚠️  Не удалось создать бэкап: {e}")
    
    # Инициализация БД
    db = DatabaseManager()
    
    # Чтение старого файла
    try:
        with open(pathbd_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return
    
    print(f"\n📊 Найдено записей: {len(lines)}")
    print("🔄 Начинаем миграцию...\n")
    
    migrated = 0
    errors = 0
    
    for idx, line in enumerate(lines, 1):
        try:
            line = line.strip()
            if not line:
                continue
            
            # Парсинг строки
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                # Попытка исправить старый формат с одинарными кавычками
                data = json.loads(line.replace("'", '"'))
            
            path = data[0]
            is_folder = len(data) == 1 or path.endswith('/')
            
            # Извлечь имя и родительский путь
            parts = path.rstrip('/').split('/')
            name = parts[-1] if parts[-1] else parts[-2] if len(parts) > 1 else ''
            
            if len(parts) > 1:
                parent_path = '/'.join(parts[:-1]) + '/'
            else:
                parent_path = '/'
            
            # Добавить в БД
            if is_folder:
                db.add_file(path, name, parent_path, is_folder=True)
                print(f"  [{idx}/{len(lines)}] 📁 {path}")
            else:
                metadata = data[1] if len(data) > 1 else {}
                
                # Извлечь расширение
                extension = os.path.splitext(name)[1].lstrip('.') if '.' in name else None
                
                db.add_file(
                    path, name, parent_path,
                    is_folder=False,
                    file_id=metadata.get('file_id'),
                    message_id=metadata.get('message_id'),
                    file_size=metadata.get('file_size', 0),
                    preview_message_id=metadata.get('preview_message_id'),
                    preview_file_id=metadata.get('preview_file_id'),
                    extension=extension
                )
                
                size_mb = metadata.get('file_size', 0) / (1024 * 1024)
                print(f"  [{idx}/{len(lines)}] 📄 {name} ({size_mb:.2f} MB)")
            
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Ошибка в строке {idx}: {str(e)[:50]}...")
    
    # Статистика
    print("\n" + "=" * 60)
    print("📈 Результаты миграции:")
    print("=" * 60)
    
    stats = db.get_statistics()
    print(f"✅ Успешно мигрировано: {migrated}")
    print(f"❌ Ошибок: {errors}")
    print(f"📁 Папок: {stats['folders_count']}")
    print(f"📄 Файлов: {stats['files_count']}")
    
    total_size_gb = (stats['total_size'] or 0) / (1024 * 1024 * 1024)
    print(f"💾 Общий размер: {total_size_gb:.2f} GB")
    
    print("\n✅ Миграция завершена!")
    print(f"📦 База данных: tgdrive.db")
    
    if backup:
        print(f"💾 Резервная копия: {backup_name}")
    
    print("\n⚠️  Рекомендация: Проверьте работу приложения перед удалением path.bd")


def verify_migration():
    """Проверка целостности миграции"""
    print("\n🔍 Проверка целостности базы данных...")
    
    db = DatabaseManager()
    
    try:
        # Проверка структуры
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['files', 'file_volumes', 'file_versions', 'shares', 'sync_metadata']
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                print(f"❌ Отсутствуют таблицы: {', '.join(missing)}")
                return False
            
            print("✅ Все таблицы созданы")
        
        # Проверка данных
        stats = db.get_statistics()
        print(f"✅ Записей в БД: {stats['total_files']}")
        
        # Проверка индексов
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"✅ Индексов создано: {len(indexes)}")
        
        print("\n✅ База данных в порядке!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False


if __name__ == "__main__":
    print("\n")
    
    # Выполнить миграцию
    migrate_from_pathbd()
    
    # Проверить результат
    verify_migration()
    
    print("\n" + "=" * 60)
    print("Готово! Теперь можно запускать TG Drive RE")
    print("=" * 60 + "\n")
