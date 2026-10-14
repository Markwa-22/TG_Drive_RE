import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional
import os

# SQL Schema for TG Drive RE
SCHEMA_SQL = """
-- Основная таблица файлов
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    parent_path TEXT,
    is_folder BOOLEAN DEFAULT 0,
    
    -- Telegram метаданные
    file_id TEXT,
    message_id INTEGER,
    file_size INTEGER DEFAULT 0,
    
    -- Превью
    preview_message_id INTEGER,
    preview_file_id TEXT,
    
    -- Метаданные файла
    mime_type TEXT,
    extension TEXT,
    
    -- Шифрование
    is_encrypted BOOLEAN DEFAULT 0,
    
    -- Многотомные архивы
    is_multivolume BOOLEAN DEFAULT 0,
    original_size INTEGER,
    compression_ratio REAL,
    
    -- Временные метки
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Индексы
    FOREIGN KEY (parent_path) REFERENCES files(path) ON DELETE CASCADE
);

-- Таблица томов для многотомных архивов
CREATE TABLE IF NOT EXISTS file_volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    volume_number INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    file_id_telegram TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(file_id, volume_number)
);

-- Таблица версий файлов
CREATE TABLE IF NOT EXISTS file_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    file_id_telegram TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    UNIQUE(file_id, version_number)
);

-- Таблица публичных ссылок (шаринг)
CREATE TABLE IF NOT EXISTS shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    share_token TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    max_downloads INTEGER DEFAULT -1,
    downloads_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Таблица синхронизации
CREATE TABLE IF NOT EXISTS sync_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metadata_message_id INTEGER UNIQUE,
    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    files_count INTEGER,
    total_size INTEGER,
    checksum TEXT
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_path);
CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_is_folder ON files(is_folder);
CREATE INDEX IF NOT EXISTS idx_files_created ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_at);

CREATE INDEX IF NOT EXISTS idx_volumes_file ON file_volumes(file_id);
CREATE INDEX IF NOT EXISTS idx_versions_file ON file_versions(file_id);
CREATE INDEX IF NOT EXISTS idx_shares_token ON shares(share_token);
CREATE INDEX IF NOT EXISTS idx_shares_active ON shares(is_active, expires_at);

-- Full-text search для быстрого поиска
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    path, 
    name, 
    content=files, 
    content_rowid=id
);

-- Триггеры для автоматического обновления FTS
CREATE TRIGGER IF NOT EXISTS files_fts_insert AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, path, name) 
    VALUES (new.id, new.path, new.name);
END;

CREATE TRIGGER IF NOT EXISTS files_fts_delete AFTER DELETE ON files BEGIN
    DELETE FROM files_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS files_fts_update AFTER UPDATE ON files BEGIN
    UPDATE files_fts 
    SET path = new.path, name = new.name 
    WHERE rowid = new.id;
END;

-- Триггер для обновления modified_at
CREATE TRIGGER IF NOT EXISTS update_modified_at AFTER UPDATE ON files
FOR EACH ROW
BEGIN
    UPDATE files SET modified_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


class DatabaseManager:
    """Менеджер базы данных для TG Drive RE"""
    
    def __init__(self, db_path='tgdrive.db'):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager для безопасной работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Доступ по именам колонок
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_database(self):
        """Инициализация БД и создание таблиц"""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
    
    # CRUD операции для файлов
    def add_file(self, path: str, name: str, parent_path: str, 
                 is_folder: bool = False, **kwargs) -> int:
        """Добавить файл/папку"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO files (path, name, parent_path, is_folder, 
                                  file_id, message_id, file_size,
                                  preview_message_id, preview_file_id,
                                  mime_type, extension, is_encrypted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                path, name, parent_path, is_folder,
                kwargs.get('file_id'), kwargs.get('message_id'), 
                kwargs.get('file_size', 0),
                kwargs.get('preview_message_id'), 
                kwargs.get('preview_file_id'),
                kwargs.get('mime_type'), kwargs.get('extension'),
                kwargs.get('is_encrypted', False)
            ))
            return cursor.lastrowid
    
    def get_file(self, path: str) -> Optional[Dict]:
        """Получить файл по пути"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM files WHERE path = ?", (path,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_folder_contents(self, parent_path: str) -> List[Dict]:
        """Получить содержимое папки"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM files 
                WHERE parent_path = ? 
                ORDER BY is_folder DESC, name ASC
            """, (parent_path,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_paths(self) -> List[str]:
        """Получить все пути (для совместимости со старым кодом)"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT path FROM files ORDER BY id")
            return [row[0] for row in cursor.fetchall()]
    
    def delete_file(self, path: str):
        """Удалить файл/папку"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
    
    def rename_file(self, old_path: str, new_path: str, new_name: str):
        """Переименовать файл"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE files 
                SET path = ?, name = ?, modified_at = CURRENT_TIMESTAMP
                WHERE path = ?
            """, (new_path, new_name, old_path))
    
    def search_files(self, query: str) -> List[Dict]:
        """Полнотекстовый поиск"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT f.* FROM files f
                JOIN files_fts fts ON f.id = fts.rowid
                WHERE files_fts MATCH ?
                ORDER BY rank
            """, (query + '*',))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Статистика использования"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(CASE WHEN is_folder = 0 THEN 1 ELSE 0 END) as files_count,
                    SUM(CASE WHEN is_folder = 1 THEN 1 ELSE 0 END) as folders_count,
                    SUM(file_size) as total_size,
                    AVG(file_size) as avg_size
                FROM files
            """)
            return dict(cursor.fetchone())
    
    # Операции с многотомными архивами
    def add_volume(self, file_id: int, volume_data: Dict):
        """Добавить том многотомного архива"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO file_volumes 
                (file_id, volume_number, message_id, file_id_telegram, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (
                file_id,
                volume_data['volume_number'],
                volume_data['message_id'],
                volume_data['file_id_telegram'],
                volume_data['file_size']
            ))
    
    def get_volumes(self, file_id: int) -> List[Dict]:
        """Получить все тома файла"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM file_volumes 
                WHERE file_id = ? 
                ORDER BY volume_number
            """, (file_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Операции с версиями файлов
    def add_version(self, file_id: int, version_data: Dict):
        """Добавить версию файла"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO file_versions 
                (file_id, version_number, message_id, file_id_telegram, 
                 file_size, comment, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                version_data['version_number'],
                version_data['message_id'],
                version_data['file_id_telegram'],
                version_data['file_size'],
                version_data.get('comment'),
                version_data.get('created_by')
            ))
    
    def get_versions(self, file_id: int) -> List[Dict]:
        """Получить все версии файла"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM file_versions 
                WHERE file_id = ? 
                ORDER BY version_number DESC
            """, (file_id,))
            return [dict(row) for row in cursor.fetchall()]
