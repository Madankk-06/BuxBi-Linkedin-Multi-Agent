import os
import logging
import requests
from typing import Optional, Any
from core.config import config

logger = logging.getLogger(__name__)

class PubloraClient:
    BASE_URL = "https://api.publora.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.PUBLORA_API_KEY
        self.platform_id = config.LINKEDIN_PLATFORM_ID

    @property
    def is_configured(self) -> bool:
        # Re-fetch from config in case .env was dynamically updated
        key = self.api_key or config.PUBLORA_API_KEY
        plat = self.platform_id or config.LINKEDIN_PLATFORM_ID
        return bool(key and plat)

    def upload_local_media(self, local_path: str) -> Optional[str]:
        """Upload a local image file to a fast HTTPS host so Publora can ingest it via mediaUrls."""
        if not os.path.exists(local_path):
            return None
        try:
            with open(local_path, "rb") as f:
                resp = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=25
                )
                if resp.status_code == 200 and resp.text.strip().startswith("http"):
                    public_url = resp.text.strip()
                    logger.info(f"Uploaded local media to public URL: {public_url}")
                    return public_url
                else:
                    logger.warning(f"Media upload failed: {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Error uploading local media for Publora: {e}")
            return None

    def publish_or_schedule_post(self, message: str, scheduled_time: Optional[str] = None, image_path: Optional[str] = None) -> dict[str, Any]:
        """Publish or schedule a LinkedIn post via Publora API."""
        api_key = self.api_key or config.PUBLORA_API_KEY
        platform_id = self.platform_id or config.LINKEDIN_PLATFORM_ID

        if not (api_key and platform_id):
            return {
                "success": False,
                "mode": "manual",
                "message": "Publora API key / Platform ID not set in .env. Add PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID to post live directly!"
            }

        headers = {
            "x-publora-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload: dict[str, Any] = {
            "content": message,
            "platforms": [platform_id]
        }
        
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time

        # Handle image attachment
        if image_path:
            if image_path.startswith("http://") or image_path.startswith("https://"):
                payload["mediaUrls"] = [image_path]
            elif os.path.exists(image_path):
                public_media_url = self.upload_local_media(image_path)
                if public_media_url:
                    payload["mediaUrls"] = [public_media_url]

        try:
            logger.info(f"Sending post request to Publora API for platform {platform_id}...")
            resp = requests.post(f"{self.BASE_URL}/create-post", json=payload, headers=headers, timeout=35)
            data = resp.json()
            if resp.status_code in (200, 201) and data.get("success"):
                logger.info(f"Publora post created successfully! Post Group ID: {data.get('postGroupId')}")
                return {
                    "success": True,
                    "post_id": data.get("postGroupId") or data.get("id"),
                    "data": data
                }
            else:
                logger.error(f"Publora error: {data}")
                return {"success": False, "error": data.get("error") or data.get("message") or str(data)}
        except Exception as e:
            logger.error(f"Failed to publish via Publora: {e}")
            return {"success": False, "error": str(e)}

publora_client = PubloraClient()
