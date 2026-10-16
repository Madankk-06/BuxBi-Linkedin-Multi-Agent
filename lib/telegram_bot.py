import os
import logging
import requests
import json
from typing import Optional, Callable
from core.config import config

logger = logging.getLogger(__name__)

class TelegramBot:
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: Optional[str] = None, default_chat_id: Optional[str] = None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.default_chat_id = default_chat_id or config.TELEGRAM_CHAT_ID
        self.api_url = f"{self.BASE_URL}{self.token}"

    def send_message(self, text: str, reply_markup: Optional[dict] = None, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> dict:
        """Send a message to Telegram."""
        if not self.token:
            logger.warning("Telegram Bot Token is not configured. Skipping send.")
            return {}

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            logger.warning("Telegram Chat ID is not configured. Skipping send.")
            return {}

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=20)
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Telegram error: {data.get('description')}")
            return data
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return {}

    def send_photo(self, photo_path_or_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
        """Send a photo by local file path or URL to Telegram."""
        if not self.token:
            return {}
        chat_id = chat_id or self.default_chat_id
        
        try:
            # If local file exists, upload as multipart/form-data
            if os.path.exists(photo_path_or_url):
                with open(photo_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": caption or "",
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(f"{self.api_url}/sendPhoto", data=data, files={"photo": f}, timeout=30)
                    return resp.json()
            else:
                # If remote URL, pass in json payload
                payload = {
                    "chat_id": chat_id,
                    "photo": photo_path_or_url,
                    "caption": caption or "",
                    "parse_mode": "HTML"
                }
                resp = requests.post(f"{self.api_url}/sendPhoto", json=payload, timeout=25)
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram photo: {e}")
            return {}

    def send_animation(self, animation_path_or_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
        """Send an animated GIF by local file path or URL to Telegram."""
        if not self.token:
            return {}
        chat_id = chat_id or self.default_chat_id

        try:
            if os.path.exists(animation_path_or_url):
                with open(animation_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": caption or "",
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(f"{self.api_url}/sendAnimation", data=data, files={"animation": f}, timeout=45)
                    return resp.json()
            else:
                payload = {
                    "chat_id": chat_id,
                    "animation": animation_path_or_url,
                    "caption": caption or "",
                    "parse_mode": "HTML"
                }
                resp = requests.post(f"{self.api_url}/sendAnimation", json=payload, timeout=30)
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram animation: {e}")
            return {}

    def download_file(self, file_id: str, dest_path: str) -> Optional[str]:
        """Download a photo/document from Telegram given its file_id."""
        if not self.token:
            return None
        try:
            # 1. Get file path from Telegram
            file_info_resp = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id}, timeout=20)
            file_info = file_info_resp.json()
            if not file_info.get("ok"):
                logger.error(f"Failed to get file info: {file_info}")
                return None
            
            file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            # 2. Download the binary stream
            dl_resp = requests.get(download_url, stream=True, timeout=30)
            if dl_resp.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in dl_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded Telegram file to {dest_path}")
                return dest_path
            else:
                logger.error(f"Download failed with status code {dl_resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading file from Telegram: {e}")
            return None

    def send_post_approval_card(self, post_id: int, topic: str, hook_formula: str, draft_text: str, image_url: Optional[str] = None):
        """Send an interactive post approval card with inline action buttons and optional visual."""
        # 1. If an image is generated, send the photo or animation first
        if image_url:
            if str(image_url).lower().endswith(".gif"):
                self.send_animation(image_url, caption=f"🎬 <b>Animated Architecture for Post #{post_id}</b>\n📌 <i>{topic}</i>")
            else:
                self.send_photo(image_url, caption=f"🎨 <b>Architecture Diagram for Post #{post_id}</b>\n📌 <i>{topic}</i>")

        char_count = len(draft_text)
        escaped_draft = draft_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        message_html = (
            f"<b>🚀 NEW GEN AI LINKEDIN POST DRAFT</b>\n\n"
            f"<b>📌 Topic:</b> {topic}\n"
            f"<b>🎯 Hook Formula:</b> <code>{hook_formula}</code>\n"
            f"<b>📊 Length:</b> {char_count} chars (sweet spot: 900-1,300)\n\n"
            f"<b>--- Post Preview ---</b>\n\n"
            f"{escaped_draft}\n\n"
            f"<b>---------------------</b>\n"
            f"<i>Tap an option below to manage this post:</i>"
        )

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📸 Add Custom Image", "callback_data": f"upload_image:{post_id}"},
                    {"text": "✅ Approve & Post Now", "callback_data": f"approve_now:{post_id}"}
                ],
                [
                    {"text": "📅 Schedule (08:30)", "callback_data": f"schedule_slot:{post_id}"},
                    {"text": "🔄 Regenerate Angle", "callback_data": f"regen_post:{post_id}"}
                ],
                [
                    {"text": "❌ Discard", "callback_data": f"discard_post:{post_id}"}
                ]
            ]
        }

        return self.send_message(message_html, reply_markup=inline_keyboard)

    def send_final_confirmation_card(self, post_id: int, topic: str, draft_text: str, image_url: str, theme_name: Optional[str] = None, chat_id: Optional[str] = None, public_media_url: Optional[str] = None):
        """Send preview of post with attached image and ask for final confirmation before posting."""
        theme_caption = f"\n🎨 <b>Theme:</b> {theme_name}" if theme_name else ""
        caption = (
            f"🖼 <b>Post Preview with Your Attached Image</b>{theme_caption}\n"
            f"📌 <b>Topic:</b> {topic}\n\n"
            f"Does this look good and ready to post to LinkedIn?"
        )
        if image_url.lower().endswith(".gif"):
            self.send_animation(image_url, caption=caption, chat_id=chat_id)
        else:
            self.send_photo(image_url, caption=caption, chat_id=chat_id)

        escaped_draft = draft_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        media_line = f"\n🖼 <b>Media URL:</b> {public_media_url}\n" if public_media_url else ""
        message_html = (
            f"<b>📋 Final Post Draft for Post #{post_id}</b>\n\n"
            f"{escaped_draft}\n"
            f"{media_line}\n"
            f"<i>Tap below to confirm and post:</i>"
        )

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🚀 Confirm & Post to LinkedIn", "callback_data": f"confirm_post:{post_id}"}
                ],
                [
                    {"text": "📸 Change Image", "callback_data": f"upload_image:{post_id}"},
                    {"text": "❌ Discard", "callback_data": f"discard_post:{post_id}"}
                ]
            ]
        }
        return self.send_message(message_html, reply_markup=inline_keyboard, chat_id=chat_id)

    def send_connection_lead_card(self, lead_id: int, name: str, title: str, company: str, 
                                  profile_url: str, why_relevant: str, note: str):
        """Send a high-authority connection lead with 1-click profile link and copyable note."""
        escaped_note = note.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        message_html = (
            f"<b>🤝 HIGH-AUTHORITY GEN AI CONNECTION LEAD</b>\n\n"
            f"<b>👤 Name:</b> {name}\n"
            f"<b>💼 Title:</b> {title} ({company})\n"
            f"<b>🔗 Profile:</b> <a href=\"{profile_url}\">{profile_url}</a>\n"
            f"<b>💡 Why Connect:</b> {why_relevant}\n\n"
            f"<b>📝 Personalized Note ({len(note)}/300 chars):</b>\n"
            f"<pre>{escaped_note}</pre>\n\n"
            f"👉 <i>Open the profile link, click 'Connect' → 'Add note', and paste the text above!</i>"
        )

        return self.send_message(message_html)

    def answer_callback_query(self, callback_query_id: str, text: str):
        """Acknowledge a button tap."""
        try:
            requests.post(f"{self.api_url}/answerCallbackQuery", json={
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": False
            }, timeout=10)
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")

    def edit_message_reply_markup(self, chat_id: str, message_id: int, reply_markup: Optional[dict] = None):
        """Update or remove buttons once an action is taken."""
        try:
            requests.post(f"{self.api_url}/editMessageReplyMarkup", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": reply_markup or {"inline_keyboard": []}
            }, timeout=10)
        except Exception as e:
            logger.error(f"Error updating message markup: {e}")

telegram_bot = TelegramBot()
