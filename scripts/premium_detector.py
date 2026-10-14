"""
Telegram Premium Detection and Configuration
Автоопределение Telegram Premium статуса
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PremiumDetector:
    """Определение Telegram Premium статуса пользователя"""
    
    # File size limits
    STANDARD_LIMIT = 2_000_000_000  # 2 GB for standard users
    PREMIUM_LIMIT = 4_000_000_000   # 4 GB for premium users
    
    # Safe limits for multi-volume splitting (leave some margin)
    STANDARD_SAFE_LIMIT = 1_900_000_000  # 1.9 GB
    PREMIUM_SAFE_LIMIT = 3_900_000_000   # 3.9 GB
    
    def __init__(self):
        self.is_premium: Optional[bool] = None
        self.file_size_limit = self.STANDARD_LIMIT
        self.safe_split_limit = self.STANDARD_SAFE_LIMIT
        
    def detect_premium_pyrogram(self, app) -> bool:
        """
        Определение Premium через Pyrogram
        
        Args:
            app: Pyrogram Client instance
            
        Returns:
            True если Premium, False если нет
        """
        try:
            me = app.get_me()
            
            # Pyrogram: User.is_premium attribute
            if hasattr(me, 'is_premium') and me.is_premium:
                self.is_premium = True
                self.file_size_limit = self.PREMIUM_LIMIT
                self.safe_split_limit = self.PREMIUM_SAFE_LIMIT
                logger.info("✨ Telegram Premium detected! File limit: 4 GB")
                return True
            else:
                self.is_premium = False
                self.file_size_limit = self.STANDARD_LIMIT
                self.safe_split_limit = self.STANDARD_SAFE_LIMIT
                logger.info("📱 Standard Telegram account. File limit: 2 GB")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to detect Premium status: {e}")
            # Default to standard limits
            self.is_premium = False
            self.file_size_limit = self.STANDARD_LIMIT
            self.safe_split_limit = self.STANDARD_SAFE_LIMIT
            return False
    
    async def detect_premium_telethon(self, client) -> bool:
        """
        Определение Premium через Telethon
        
        Args:
            client: Telethon Client instance
            
        Returns:
            True если Premium, False если нет
        """
        try:
            me = await client.get_me()
            
            # Telethon: User.premium attribute
            if hasattr(me, 'premium') and me.premium:
                self.is_premium = True
                self.file_size_limit = self.PREMIUM_LIMIT
                self.safe_split_limit = self.PREMIUM_SAFE_LIMIT
                logger.info("✨ Telegram Premium detected! File limit: 4 GB")
                return True
            else:
                self.is_premium = False
                self.file_size_limit = self.STANDARD_LIMIT
                self.safe_split_limit = self.STANDARD_SAFE_LIMIT
                logger.info("📱 Standard Telegram account. File limit: 2 GB")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to detect Premium status: {e}")
            # Default to standard limits
            self.is_premium = False
            self.file_size_limit = self.STANDARD_LIMIT
            self.safe_split_limit = self.STANDARD_SAFE_LIMIT
            return False
    
    def set_premium_manual(self, is_premium: bool):
        """
        Ручная установка Premium статуса
        
        Args:
            is_premium: True для Premium, False для стандартного
        """
        self.is_premium = is_premium
        
        if is_premium:
            self.file_size_limit = self.PREMIUM_LIMIT
            self.safe_split_limit = self.PREMIUM_SAFE_LIMIT
            logger.info("✨ Premium mode enabled manually. File limit: 4 GB")
        else:
            self.file_size_limit = self.STANDARD_LIMIT
            self.safe_split_limit = self.STANDARD_SAFE_LIMIT
            logger.info("📱 Standard mode enabled manually. File limit: 2 GB")
    
    def get_file_size_limit(self) -> int:
        """Получить текущий лимит размера файла"""
        return self.file_size_limit
    
    def get_safe_split_limit(self) -> int:
        """Получить безопасный лимит для разбиения на тома"""
        return self.safe_split_limit
    
    def needs_splitting(self, file_size: int) -> bool:
        """
        Проверить нужно ли разбивать файл на тома
        
        Args:
            file_size: размер файла в байтах
            
        Returns:
            True если нужно разбивать
        """
        return file_size > self.safe_split_limit
    
    def get_status_info(self) -> dict:
        """Получить информацию о текущем статусе"""
        return {
            'is_premium': self.is_premium,
            'file_size_limit': self.file_size_limit,
            'file_size_limit_gb': self.file_size_limit / 1_000_000_000,
            'safe_split_limit': self.safe_split_limit,
            'safe_split_limit_gb': self.safe_split_limit / 1_000_000_000,
            'mode': 'Premium' if self.is_premium else 'Standard'
        }
    
    def format_limit(self) -> str:
        """Форматированный вывод лимита"""
        gb = self.file_size_limit / 1_000_000_000
        mode = "Premium" if self.is_premium else "Standard"
        return f"{mode} mode: {gb:.1f} GB limit"


# Global instance
_premium_detector = PremiumDetector()


def get_premium_detector() -> PremiumDetector:
    """Получить глобальный экземпляр детектора Premium"""
    return _premium_detector


def detect_premium(app=None, telethon_client=None, manual: Optional[bool] = None) -> bool:
    """
    Удобная функция для определения Premium статуса
    
    Args:
        app: Pyrogram client (optional)
        telethon_client: Telethon client (optional)
        manual: Ручная установка статуса (optional)
        
    Returns:
        True если Premium
    """
    detector = get_premium_detector()
    
    if manual is not None:
        detector.set_premium_manual(manual)
        return manual
    
    if app:
        return detector.detect_premium_pyrogram(app)
    
    if telethon_client:
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(detector.detect_premium_telethon(telethon_client))
    
    logger.warning("No client provided for Premium detection, using standard limits")
    return False
