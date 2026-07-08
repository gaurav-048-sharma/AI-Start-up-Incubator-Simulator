"""
Local storage service for managing file uploads (reports, pitch decks, etc.).
"""

import os
import structlog
from typing import Optional
from app.config import get_settings

logger = structlog.get_logger()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

class StorageService:
    """Manages file uploads/downloads locally."""

    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

    async def upload_report(
        self,
        idea_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> Optional[str]:
        try:
            idea_dir = os.path.join(UPLOAD_DIR, idea_id)
            os.makedirs(idea_dir, exist_ok=True)
            path = os.path.join(idea_dir, filename)
            with open(path, "wb") as f:
                f.write(content)
            
            settings = get_settings()
            url = f"http://{settings.api_host}:{settings.api_port}/static/{idea_id}/{filename}"
            logger.info("Report uploaded", idea_id=idea_id, filename=filename)
            return url
        except Exception as e:
            logger.error("Failed to upload report", error=str(e))
            return None

    async def upload_pitch_deck(
        self,
        idea_id: str,
        filename: str,
        content: bytes,
    ) -> Optional[str]:
        try:
            idea_dir = os.path.join(UPLOAD_DIR, idea_id)
            os.makedirs(idea_dir, exist_ok=True)
            path = os.path.join(idea_dir, filename)
            with open(path, "wb") as f:
                f.write(content)
            
            settings = get_settings()
            url = f"http://{settings.api_host}:{settings.api_port}/static/{idea_id}/{filename}"
            logger.info("Pitch deck uploaded", idea_id=idea_id, filename=filename)
            return url
        except Exception as e:
            logger.error("Failed to upload pitch deck", error=str(e))
            return None

    async def get_file_url(self, bucket: str, path: str) -> Optional[str]:
        settings = get_settings()
        return f"http://{settings.api_host}:{settings.api_port}/static/{path}"

    async def delete_file(self, bucket: str, path: str) -> bool:
        try:
            full_path = os.path.join(UPLOAD_DIR, path)
            if os.path.exists(full_path):
                os.remove(full_path)
            return True
        except Exception as e:
            logger.error("Failed to delete file", error=str(e))
            return False


_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
