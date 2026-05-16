"""
Supabase storage service for managing file uploads (reports, pitch decks, etc.).
"""

import structlog
from typing import Optional

from app.models.database import get_supabase_client

logger = structlog.get_logger()

REPORTS_BUCKET = "reports"
PITCH_DECKS_BUCKET = "pitch-decks"
ASSETS_BUCKET = "assets"


class StorageService:
    """Manages file uploads/downloads to Supabase Storage."""

    def __init__(self):
        self._client = get_supabase_client()

    async def upload_report(
        self,
        idea_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> Optional[str]:
        """Upload a report file and return the public URL."""
        try:
            path = f"{idea_id}/{filename}"
            self._client.storage.from_(REPORTS_BUCKET).upload(
                path=path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            url = self._client.storage.from_(REPORTS_BUCKET).get_public_url(path)
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
        """Upload a pitch deck file and return the public URL."""
        try:
            path = f"{idea_id}/{filename}"
            self._client.storage.from_(PITCH_DECKS_BUCKET).upload(
                path=path,
                file=content,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
            url = self._client.storage.from_(PITCH_DECKS_BUCKET).get_public_url(path)
            logger.info("Pitch deck uploaded", idea_id=idea_id, filename=filename)
            return url
        except Exception as e:
            logger.error("Failed to upload pitch deck", error=str(e))
            return None

    async def get_file_url(self, bucket: str, path: str) -> Optional[str]:
        """Get the public URL for a file in storage."""
        try:
            return self._client.storage.from_(bucket).get_public_url(path)
        except Exception as e:
            logger.error("Failed to get file URL", error=str(e))
            return None

    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete a file from storage."""
        try:
            self._client.storage.from_(bucket).remove([path])
            logger.info("File deleted", bucket=bucket, path=path)
            return True
        except Exception as e:
            logger.error("Failed to delete file", error=str(e))
            return False


_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
