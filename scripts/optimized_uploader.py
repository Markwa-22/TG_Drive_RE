"""
Optimized Telegram Uploader with Multi-DC Support and Adaptive Chunking
Handles FloodWait, speed optimization, and data center switching
"""

import asyncio
import time
import logging
from typing import Optional, Callable, List, Dict
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError, FileMigrateError, FilePartMissingError
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

logger = logging.getLogger(__name__)


class DCManager:
    """Manages multiple Telegram Data Centers for optimal speed"""
    
    # Telegram DC locations and typical speeds
    DC_INFO = {
        1: {"location": "Miami, USA", "typical_speed": "medium"},
        2: {"location": "Amsterdam, Netherlands", "typical_speed": "high"},
        3: {"location": "Miami, USA", "typical_speed": "medium"},
        4: {"location": "Amsterdam, Netherlands", "typical_speed": "high"},
        5: {"location": "Singapore", "typical_speed": "low"}
    }
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.current_dc = None
        self.dc_speeds: Dict[int, float] = {}
        
    async def get_current_dc(self) -> int:
        """Get current data center ID"""
        if self.current_dc is None:
            me = await self.client.get_me()
            self.current_dc = me.photo.dc_id if me.photo else 2
        return self.current_dc
    
    async def test_dc_speed(self, dc_id: int, test_size: int = 100_000) -> float:
        """Test upload speed to specific DC (returns bytes/sec)"""
        try:
            test_data = b'0' * test_size
            start_time = time.time()
            
            # Upload small test file
            await self.client.upload_file(
                test_data,
                part_size_kb=64
            )
            
            elapsed = time.time() - start_time
            speed = test_size / elapsed if elapsed > 0 else 0
            
            self.dc_speeds[dc_id] = speed
            logger.info(f"DC {dc_id} speed: {speed / 1024:.2f} KB/s")
            return speed
            
        except Exception as e:
            logger.warning(f"Failed to test DC {dc_id}: {e}")
            return 0
    
    async def find_fastest_dc(self, test_dcs: List[int] = None) -> int:
        """Find fastest available DC"""
        if test_dcs is None:
            test_dcs = [1, 2, 4]  # Most reliable DCs
        
        logger.info("Testing DC speeds...")
        speeds = {}
        
        for dc_id in test_dcs:
            speed = await self.test_dc_speed(dc_id)
            if speed > 0:
                speeds[dc_id] = speed
        
        if not speeds:
            return await self.get_current_dc()
        
        fastest_dc = max(speeds, key=speeds.get)
        logger.info(f"Fastest DC: {fastest_dc} ({speeds[fastest_dc] / 1024:.2f} KB/s)")
        return fastest_dc
    
    async def switch_dc(self, dc_id: int) -> bool:
        """Switch to different DC"""
        try:
            await self.client._switch_dc(dc_id)
            self.current_dc = dc_id
            logger.info(f"Switched to DC {dc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to DC {dc_id}: {e}")
            return False


class AdaptiveChunker:
    """Dynamically adjusts chunk size based on file size and upload speed"""
    
    # Chunk size ranges (in KB)
    MIN_CHUNK_SIZE = 64
    MAX_CHUNK_SIZE = 512
    DEFAULT_CHUNK_SIZE = 256
    
    def __init__(self):
        self.current_chunk_size = self.DEFAULT_CHUNK_SIZE
        self.speed_history: List[float] = []
        self.max_history = 10
        
    def get_optimal_chunk_size(self, file_size: int) -> int:
        """Calculate optimal chunk size based on file size"""
        if file_size < 10 * 1024 * 1024:  # <10MB
            return 128
        elif file_size < 100 * 1024 * 1024:  # <100MB
            return 256
        elif file_size < 500 * 1024 * 1024:  # <500MB
            return 384
        else:  # >500MB
            return 512
    
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
            logger.debug(f"Reduced chunk size to {self.current_chunk_size}KB")
        
        # If speed is good, try increasing chunk size
        elif avg_speed > target_speed * 0.9:  # >90% of target
            self.current_chunk_size = min(
                self.MAX_CHUNK_SIZE,
                int(self.current_chunk_size * 1.25)
            )
            logger.debug(f"Increased chunk size to {self.current_chunk_size}KB")
        
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
        
    async def handle_flood_wait(self, error: FloodWaitError, callback: Optional[Callable] = None):
        """Handle FloodWait error with smart backoff"""
        wait_time = min(error.seconds, self.max_delay)
        self.flood_wait_count += 1
        
        logger.warning(
            f"FloodWait #{self.flood_wait_count}: waiting {wait_time}s "
            f"(requested: {error.seconds}s)"
        )
        
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
                
            except FloodWaitError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Max retries ({max_retries}) reached")
                    raise
                
                await self.handle_flood_wait(e, progress_callback)
                
            except (FileMigrateError, FilePartMissingError) as e:
                logger.warning(f"File error: {e}, retrying...")
                retry_count += 1
                await asyncio.sleep(self.current_delay)
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        
        raise Exception(f"Failed after {max_retries} retries")
    
    def reset(self):
        """Reset handler state"""
        self.current_delay = self.initial_delay
        self.flood_wait_count = 0


class OptimizedUploader:
    """
    Optimized Telegram file uploader with:
    - Multi-DC support
    - Adaptive chunk sizing
    - Smart FloodWait handling
    - Speed monitoring
    """
    
    def __init__(self, client: TelegramClient):
        self.client = client
        self.dc_manager = DCManager(client)
        self.chunker = AdaptiveChunker()
        self.flood_handler = FloodWaitHandler()
        
        self.total_uploaded = 0
        self.upload_start_time = 0
        self.current_speed = 0
        
    async def initialize(self, auto_select_dc: bool = True):
        """Initialize uploader and optionally select fastest DC"""
        if auto_select_dc:
            fastest_dc = await self.dc_manager.find_fastest_dc()
            await self.dc_manager.switch_dc(fastest_dc)
    
    def get_upload_stats(self) -> Dict:
        """Get current upload statistics"""
        elapsed = time.time() - self.upload_start_time if self.upload_start_time > 0 else 1
        avg_speed = self.total_uploaded / elapsed
        
        return {
            "total_uploaded": self.total_uploaded,
            "elapsed_time": elapsed,
            "average_speed": avg_speed,
            "current_speed": self.current_speed,
            "current_dc": self.dc_manager.current_dc,
            "chunk_size": self.chunker.current_chunk_size,
            "flood_wait_count": self.flood_handler.flood_wait_count
        }
    
    async def upload_file(
        self,
        file_path: Path,
        chat_id: int,
        caption: str = "",
        progress_callback: Optional[Callable] = None,
        use_adaptive_chunking: bool = True
    ):
        """
        Upload file with all optimizations enabled
        
        Args:
            file_path: Path to file
            chat_id: Telegram chat ID
            caption: File caption
            progress_callback: Callback(uploaded_bytes, total_bytes, speed, stats)
            use_adaptive_chunking: Enable adaptive chunk size adjustment
        """
        file_size = file_path.stat().st_size
        
        # Initialize
        self.total_uploaded = 0
        self.upload_start_time = time.time()
        
        # Determine optimal chunk size
        chunk_size_kb = self.chunker.get_optimal_chunk_size(file_size)
        logger.info(
            f"Uploading {file_path.name} ({file_size / 1024 / 1024:.2f} MB) "
            f"with {chunk_size_kb}KB chunks"
        )
        
        # Progress tracking
        last_update_time = time.time()
        last_uploaded = 0
        
        async def upload_progress(current, total):
            nonlocal last_update_time, last_uploaded
            
            self.total_uploaded = current
            current_time = time.time()
            
            # Calculate speed every second
            if current_time - last_update_time >= 1.0:
                bytes_since_last = current - last_uploaded
                time_elapsed = current_time - last_update_time
                self.current_speed = bytes_since_last / time_elapsed
                
                # Adaptive chunking
                if use_adaptive_chunking and current < total:
                    new_chunk_size = self.chunker.adjust_chunk_size(self.current_speed)
                    if new_chunk_size != chunk_size_kb:
                        logger.debug(f"Adjusted chunk size: {chunk_size_kb}KB -> {new_chunk_size}KB")
                
                last_update_time = current_time
                last_uploaded = current
            
            # User callback
            if progress_callback:
                stats = self.get_upload_stats()
                await progress_callback(current, total, self.current_speed, stats)
        
        # Upload with retry logic
        async def do_upload():
            return await self.client.send_file(
                chat_id,
                file_path,
                caption=caption,
                part_size_kb=chunk_size_kb,
                progress_callback=upload_progress
            )
        
        try:
            message = await self.flood_handler.execute_with_retry(
                do_upload,
                max_retries=5,
                progress_callback=progress_callback
            )
            
            # Log final stats
            stats = self.get_upload_stats()
            logger.info(
                f"Upload complete: {file_path.name} "
                f"({stats['average_speed'] / 1024 / 1024:.2f} MB/s avg, "
                f"{stats['flood_wait_count']} flood waits)"
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
        finally:
            # Reset for next upload
            self.chunker.reset()
            self.flood_handler.reset()
    
    async def download_file(
        self,
        message,
        output_path: Path,
        progress_callback: Optional[Callable] = None
    ):
        """Download file with optimizations"""
        file_size = message.file.size if message.file else 0
        
        self.total_uploaded = 0  # Reuse for download tracking
        self.upload_start_time = time.time()
        
        # Determine optimal chunk size for download
        chunk_size_kb = self.chunker.get_optimal_chunk_size(file_size)
        
        logger.info(
            f"Downloading {message.file.name} ({file_size / 1024 / 1024:.2f} MB) "
            f"with {chunk_size_kb}KB chunks"
        )
        
        last_update_time = time.time()
        last_downloaded = 0
        
        async def download_progress(current, total):
            nonlocal last_update_time, last_downloaded
            
            self.total_uploaded = current
            current_time = time.time()
            
            if current_time - last_update_time >= 1.0:
                bytes_since_last = current - last_downloaded
                time_elapsed = current_time - last_update_time
                self.current_speed = bytes_since_last / time_elapsed
                
                last_update_time = current_time
                last_downloaded = current
            
            if progress_callback:
                stats = self.get_upload_stats()
                await progress_callback(current, total, self.current_speed, stats)
        
        async def do_download():
            return await self.client.download_media(
                message,
                file=str(output_path),
                progress_callback=download_progress
            )
        
        try:
            result = await self.flood_handler.execute_with_retry(
                do_download,
                max_retries=5,
                progress_callback=progress_callback
            )
            
            stats = self.get_upload_stats()
            logger.info(
                f"Download complete: {message.file.name} "
                f"({stats['average_speed'] / 1024 / 1024:.2f} MB/s avg)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
        finally:
            self.chunker.reset()
            self.flood_handler.reset()


# Convenience functions
async def create_optimized_uploader(
    client: TelegramClient,
    auto_select_dc: bool = True
) -> OptimizedUploader:
    """Create and initialize optimized uploader"""
    uploader = OptimizedUploader(client)
    await uploader.initialize(auto_select_dc)
    return uploader
