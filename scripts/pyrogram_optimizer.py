"""
Pyrogram-compatible upload/download optimizer
Адаптированная версия optimized_uploader.py для работы с Pyrogram
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Dict, List
from pathlib import Path
from pyrogram import Client
from pyrogram.errors import FloodWait

logger = logging.getLogger(__name__)


class AdaptiveChunker:
    """Dynamically adjusts chunk size based on file size and upload speed"""
    
    # Chunk size ranges (in bytes for Pyrogram)
    MIN_CHUNK_SIZE = 64 * 1024      # 64KB
    MAX_CHUNK_SIZE = 512 * 1024     # 512KB
    DEFAULT_CHUNK_SIZE = 256 * 1024 # 256KB
    
    def __init__(self):
        self.current_chunk_size = self.DEFAULT_CHUNK_SIZE
        self.speed_history: List[float] = []
        self.max_history = 10
        
    def get_optimal_chunk_size(self, file_size: int) -> int:
        """Calculate optimal chunk size based on file size (returns bytes)"""
        if file_size < 10 * 1024 * 1024:  # <10MB
            return 128 * 1024  # 128KB
        elif file_size < 100 * 1024 * 1024:  # <100MB
            return 256 * 1024  # 256KB
        elif file_size < 500 * 1024 * 1024:  # <500MB
            return 384 * 1024  # 384KB
        else:  # >500MB
            return 512 * 1024  # 512KB
    
    def adjust_chunk_size(self, current_speed: float, target_speed: float = 1_000_000) -> int:
        """Adjust chunk size based on current upload speed"""
        self.speed_history.append(current_speed)
        if len(self.speed_history) > self.max_history:
            self.speed_history.pop(0)
        
        avg_speed = sum(self.speed_history) / len(self.speed_history)
        
        # If speed is too low, reduce chunk size
        if avg_speed < target_speed * 0.5:  # <50% of target
            self.current_chunk_size = max(
                self.MIN_CHUNK_SIZE,
                int(self.current_chunk_size * 0.75)
            )
        
        # If speed is good, try increasing chunk size
        elif avg_speed > target_speed * 0.9:  # >90% of target
            self.current_chunk_size = min(
                self.MAX_CHUNK_SIZE,
                int(self.current_chunk_size * 1.25)
            )
        
        return self.current_chunk_size
    
    def reset(self):
        """Reset to default settings"""
        self.current_chunk_size = self.DEFAULT_CHUNK_SIZE
        self.speed_history.clear()


class FloodWaitHandler:
    """Smart FloodWait error handling with exponential backoff"""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 300.0):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.current_delay = initial_delay
        self.flood_wait_count = 0
        
    async def handle_flood_wait(self, error: FloodWait, callback: Optional[Callable] = None):
        """Handle FloodWait error with smart backoff"""
        wait_time = min(error.value, self.max_delay)
        self.flood_wait_count += 1
        
        print(f"⏳ FloodWait: ожидание {wait_time}s...")
        
        if callback:
            await callback(wait_time, self.flood_wait_count)
        
        await asyncio.sleep(wait_time)
        
        # Exponential backoff for future requests
        self.current_delay = min(self.current_delay * 1.5, self.max_delay)
    
    async def execute_with_retry(
        self,
        func,
        max_retries: int = 5,
        progress_callback: Optional[Callable] = None
    ):
        """Execute function with automatic retry on FloodWait"""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await func()
                # Success - reset delay
                self.current_delay = self.initial_delay
                return result
                
            except FloodWait as e:
                retry_count += 1
                if retry_count >= max_retries:
                    print(f"❌ Достигнут лимит повторов ({max_retries})")
                    raise
                
                await self.handle_flood_wait(e, progress_callback)
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                raise
        
        raise Exception(f"Failed after {max_retries} retries")
    
    def reset(self):
        """Reset handler state"""
        self.current_delay = self.initial_delay
        self.flood_wait_count = 0


class PyrogramOptimizer:
    """
    Optimized Pyrogram file uploader/downloader with:
    - Adaptive chunk sizing
    - Smart FloodWait handling
    - Speed monitoring
    """
    
    def __init__(self):
        self.chunker = AdaptiveChunker()
        self.flood_handler = FloodWaitHandler()
        
        self.total_transferred = 0
        self.transfer_start_time = 0
        self.current_speed = 0
        
    def get_stats(self) -> Dict:
        """Get current transfer statistics"""
        elapsed = time.time() - self.transfer_start_time if self.transfer_start_time > 0 else 1
        avg_speed = self.total_transferred / elapsed
        
        return {
            "total_transferred": self.total_transferred,
            "elapsed_time": elapsed,
            "average_speed": avg_speed,
            "current_speed": self.current_speed,
            "chunk_size": self.chunker.current_chunk_size,
            "flood_wait_count": self.flood_handler.flood_wait_count
        }
    
    def create_progress_callback(
        self,
        user_callback: Optional[Callable] = None,
        use_adaptive_chunking: bool = True
    ):
        """
        Create optimized progress callback for Pyrogram
        
        Args:
            user_callback: User's progress callback(current, total, speed, stats)
            use_adaptive_chunking: Enable adaptive chunk size adjustment
        
        Returns:
            Progress callback function for Pyrogram
        """
        last_update_time = time.time()
        last_transferred = 0
        
        async def progress_callback(current, total):
            nonlocal last_update_time, last_transferred
            
            self.total_transferred = current
            current_time = time.time()
            
            # Calculate speed every 2 seconds (reduced overhead)
            if current_time - last_update_time >= 2.0:
                bytes_since_last = current - last_transferred
                time_elapsed = current_time - last_update_time
                self.current_speed = bytes_since_last / time_elapsed
                
                last_update_time = current_time
                last_transferred = current
            
            # User callback - simplified, no stats
            if user_callback:
                # Check if callback is async or sync
                result = user_callback(current, total, self.current_speed, None)
                if result is not None:
                    await result
        
        return progress_callback
    
    async def upload_with_retry(
        self,
        client: Client,
        chat_id: str,
        file_path: str,
        caption: str = "",
        progress_callback: Optional[Callable] = None,
        use_adaptive_chunking: bool = True,
        max_retries: int = 5
    ):
        """
        Upload file with optimizations and retry logic
        
        Args:
            client: Pyrogram Client
            chat_id: Target chat ID
            file_path: Path to file
            caption: File caption
            progress_callback: User progress callback
            use_adaptive_chunking: Enable adaptive chunking
            max_retries: Maximum retry attempts
        
        Returns:
            Pyrogram Message object
        """
        file_size = Path(file_path).stat().st_size
        
        # Initialize
        self.total_transferred = 0
        self.transfer_start_time = time.time()
        
        # Create simplified progress callback (no adaptive chunking overhead)
        optimized_progress = self.create_progress_callback(
            progress_callback,
            use_adaptive_chunking=False  # Disabled - Pyrogram doesn't support it
        )
        
        # Upload with retry logic
        async def do_upload():
            return await client.send_document(
                chat_id,
                file_path,
                caption=caption,
                progress=optimized_progress,
                file_name=Path(file_path).name
            )
        
        try:
            message = await self.flood_handler.execute_with_retry(
                do_upload,
                max_retries=max_retries,
                progress_callback=progress_callback
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
        finally:
            # Reset for next transfer
            self.flood_handler.reset()
    
    async def download_with_retry(
        self,
        client: Client,
        message_or_file_id,
        file_name: str,
        progress_callback: Optional[Callable] = None,
        use_adaptive_chunking: bool = True,
        max_retries: int = 5
    ):
        """
        Download file with optimizations and retry logic
        
        Args:
            client: Pyrogram Client
            message_or_file_id: Message object or file_id
            file_name: Output file path
            progress_callback: User progress callback
            use_adaptive_chunking: Enable adaptive chunking
            max_retries: Maximum retry attempts
        
        Returns:
            Downloaded file path
        """
        # Initialize
        self.total_transferred = 0
        self.transfer_start_time = time.time()
        
        # Create simplified progress callback (no adaptive chunking overhead)
        optimized_progress = self.create_progress_callback(
            progress_callback,
            use_adaptive_chunking=False  # Disabled - Pyrogram doesn't support it
        )
        
        # Download with retry logic
        async def do_download():
            return await client.download_media(
                message_or_file_id,
                file_name=file_name,
                progress=optimized_progress
            )
        
        try:
            result = await self.flood_handler.execute_with_retry(
                do_download,
                max_retries=max_retries,
                progress_callback=progress_callback
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
        finally:
            # Reset for next transfer
            self.flood_handler.reset()


# Global optimizer instance
_global_optimizer = None

def get_optimizer() -> PyrogramOptimizer:
    """Get or create global optimizer instance"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = PyrogramOptimizer()
    return _global_optimizer
