import os
import re
import logging
import requests
from datetime import datetime, timedelta, timezone
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

    def _resolve_scheduled_time(self, scheduled_time: Optional[str]) -> str:
        """Resolve scheduled_time into ISO-8601 UTC format (YYYY-MM-DDTHH:MM:SSZ).

        CRITICAL PUBLORA API RULE:
        Publora treats a missing `scheduledTime` as 'Save as Draft' (status='draft')
        and NEVER publishes it to LinkedIn unless `scheduledTime` is provided.
        Therefore, for 'Post Now' (scheduled_time=None), we schedule 60 seconds in
        the future in UTC ISO-8601 format so Publora immediately queues and posts it.
        """
        now_utc = datetime.now(timezone.utc)

        if not scheduled_time:
            # Immediate publish -> 60 seconds from now in UTC
            target_utc = now_utc + timedelta(seconds=60)
            return target_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        # If HH:MM format (e.g. "08:30"), convert from IST (UTC+5:30) to next occurrence in UTC
        if re.match(r"^\d{1,2}:\d{2}$", scheduled_time.strip()):
            hour, minute = map(int, scheduled_time.strip().split(":"))
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            now_ist = datetime.now(ist_tz)
            target_ist = now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_ist <= now_ist:
                target_ist += timedelta(days=1)
            return target_ist.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Already ISO-8601
        return scheduled_time

    def upload_local_media(self, local_path: str, post_id: Optional[int] = None) -> Optional[str]:
        """Upload a local image file to a fast HTTPS host so Publora/LinkedIn can ingest it via mediaUrls."""
        if not os.path.exists(local_path):
            return None

        # Tier 1: Catbox (permanent, global CDN, perfect for LinkedIn and browsers)
        for attempt in range(2):
            try:
                with open(local_path, "rb") as f:
                    resp = requests.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": f},
                        timeout=35
                    )
                    if resp.status_code == 200 and resp.text.strip().startswith("http"):
                        public_url = resp.text.strip()
                        logger.info(f"Uploaded local media to Catbox: {public_url}")
                        return public_url
            except Exception as e:
                logger.warning(f"Catbox upload attempt {attempt+1} failed: {e}")
                time.sleep(1)

        # Tier 2: Litterbox (72h temporary HTTPS host)
        try:
            with open(local_path, "rb") as f:
                resp = requests.post(
                    "https://litterbox.catbox.moe/resources/internals/api.php",
                    data={"reqtype": "fileupload", "time": "72h"},
                    files={"fileToUpload": f},
                    timeout=30
                )
                if resp.status_code == 200 and resp.text.strip().startswith("http"):
                    public_url = resp.text.strip()
                    logger.info(f"Uploaded local media to Litterbox: {public_url}")
                    return public_url
        except Exception as e:
            logger.warning(f"Litterbox upload failed: {e}")

        # Tier 3: First-party database raw link or media fallback
        render_url = os.getenv("RENDER_EXTERNAL_URL", "https://buxbi.onrender.com").rstrip("/")
        if post_id:
            fallback_url = f"{render_url}/dl/raw/{post_id}"
        else:
            filename = os.path.basename(local_path)
            fallback_url = f"{render_url}/media/{filename}"
        logger.info(f"Using first-party media URL fallback: {fallback_url}")
        return fallback_url

    def get_post_status(self, post_group_id: str) -> dict[str, Any]:
        """Query Publora for the live status of a post group."""
        api_key = self.api_key or config.PUBLORA_API_KEY
        if not api_key or not post_group_id:
            return {}
        headers = {
            "x-publora-key": api_key,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(f"{self.BASE_URL}/get-post/{post_group_id}", headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def publish_or_schedule_post(
        self,
        message: str,
        scheduled_time: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> dict[str, Any]:
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

        resolved_schedule_utc = self._resolve_scheduled_time(scheduled_time)

        payload: dict[str, Any] = {
            "content": message,
            "platforms": [platform_id],
            "scheduledTime": resolved_schedule_utc
        }

        # Handle image attachment
        public_media_url = None
        if image_path:
            if image_path.startswith("http://") or image_path.startswith("https://"):
                public_media_url = image_path
                payload["mediaUrls"] = [public_media_url]
            elif os.path.exists(image_path):
                public_media_url = self.upload_local_media(image_path)
                if public_media_url:
                    payload["mediaUrls"] = [public_media_url]

        try:
            logger.info(
                f"Sending post request to Publora API for platform {platform_id} "
                f"(scheduledTime={resolved_schedule_utc}, media={public_media_url})..."
            )
            resp = requests.post(f"{self.BASE_URL}/create-post", json=payload, headers=headers, timeout=35)
            data = resp.json()
            if resp.status_code in (200, 201) and data.get("success"):
                post_group_id = data.get("postGroupId") or data.get("id")
                logger.info(f"Publora post scheduled for live dispatch! Post Group ID: {post_group_id}")
                return {
                    "success": True,
                    "post_id": post_group_id,
                    "scheduled_time_utc": data.get("scheduledTime") or resolved_schedule_utc,
                    "media_url": public_media_url,
                    "data": data
                }
            else:
                logger.error(f"Publora error: {data}")
                return {"success": False, "error": data.get("error") or data.get("message") or str(data)}
        except Exception as e:
            logger.error(f"Failed to publish via Publora: {e}")
            return {"success": False, "error": str(e)}

publora_client = PubloraClient()
