import os
import re
import logging
import requests
from typing import Optional
from pathlib import Path
from core.config import config

logger = logging.getLogger(__name__)

def _esc(val: Optional[str]) -> str:
    """Safely HTML-escape dynamic strings for Telegram HTML parse_mode and strip asterisks/arrows."""
    if not val:
        return ""
    cleaned = str(val).replace("**", "").replace("*", "")
    for sym in ("↳", "→", "⇒", "▸", "▹", "➢", "➤"):
        cleaned = cleaned.replace(sym, "•")
    return cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class TelegramBot:
    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: Optional[str] = None, default_chat_id: Optional[str] = None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.default_chat_id = default_chat_id or config.TELEGRAM_CHAT_ID
        self.api_url = f"{self.BASE_URL}{self.token}"

    def set_bot_commands(self) -> dict:
        """Register the 1-click '/' command menu in Telegram chat bar."""
        if not self.token:
            return {}
        commands = [
            {"command": "draft", "description": "Draft a fresh Gen AI post + GIF"},
            {"command": "post", "description": "Publish latest post to LinkedIn"},
            {"command": "connections", "description": "Get 3 connection leads and notes"},
            {"command": "repurpose", "description": "Repurpose URL/article/text to post"},
            {"command": "learn", "description": "Teach Buxbi a tech, document, or rule"},
            {"command": "topics", "description": "View stored Knowledge Vault topics"},
            {"command": "intimate", "description": "Trigger weekly knowledge refresh"},
            {"command": "status", "description": "Check 24/7 cloud container status"},
            {"command": "help", "description": "Show all commands and guides"}
        ]
        try:
            resp = requests.post(f"{self.api_url}/setMyCommands", json={"commands": commands}, timeout=15)
            logger.info(f"Registered Telegram bot '/' commands: {resp.status_code}")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
            return {}

    def send_message(self, text: str, reply_markup: Optional[dict] = None, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> dict:
        """Send a message to Telegram with automatic asterisk/arrow sanitization and HTML fallback."""
        if not self.token:
            logger.warning("Telegram Bot Token is not configured. Skipping send.")
            return {}

        chat_id = chat_id or self.default_chat_id
        if not chat_id:
            logger.warning("Telegram Chat ID is not configured. Skipping send.")
            return {}

        # Always strip markdown asterisks and arrow symbols from outgoing text
        clean_text = text.replace("**", "").replace("*", "")
        for sym in ("↳", "→", "⇒", "▸", "▹", "➢", "➤"):
            clean_text = clean_text.replace(sym, "•")

        payload = {
            "chat_id": chat_id,
            "text": clean_text,
            "disable_web_page_preview": False
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=20)
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"Telegram HTML send warning ({data.get('description')}), retrying as plain text...")
                plain_text = re.sub(r"<[^>]+>", "", clean_text).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                payload.pop("parse_mode", None)
                payload["text"] = plain_text
                resp2 = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=20)
                return resp2.json()
            return data
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return {}

    def send_photo(self, photo_path_or_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
        """Send a photo by local file path or URL to Telegram."""
        if not self.token:
            return {}
        chat_id = chat_id or self.default_chat_id
        clean_caption = (caption or "").replace("**", "").replace("*", "")

        try:
            if os.path.exists(photo_path_or_url):
                with open(photo_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": clean_caption,
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(f"{self.api_url}/sendPhoto", data=data, files={"photo": f}, timeout=30)
                    return resp.json()
            else:
                payload = {
                    "chat_id": chat_id,
                    "photo": photo_path_or_url,
                    "caption": clean_caption,
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
        clean_caption = (caption or "").replace("**", "").replace("*", "")

        try:
            if os.path.exists(animation_path_or_url):
                with open(animation_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": clean_caption,
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(f"{self.api_url}/sendAnimation", data=data, files={"animation": f}, timeout=45)
                    return resp.json()
            else:
                payload = {
                    "chat_id": chat_id,
                    "animation": animation_path_or_url,
                    "caption": clean_caption,
                    "parse_mode": "HTML"
                }
                resp = requests.post(f"{self.api_url}/sendAnimation", json=payload, timeout=30)
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram animation: {e}")
            return {}

    def send_document(self, document_path_or_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
        """Send an uncompressed document (raw binary file) to Telegram, bypassing image/video compression."""
        if not self.token:
            return {}
        chat_id = chat_id or self.default_chat_id
        clean_caption = (caption or "").replace("**", "").replace("*", "")

        try:
            if os.path.exists(document_path_or_url):
                with open(document_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": clean_caption,
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(f"{self.api_url}/sendDocument", data=data, files={"document": f}, timeout=60)
                    return resp.json()
            else:
                payload = {
                    "chat_id": chat_id,
                    "document": document_path_or_url,
                    "caption": clean_caption,
                    "parse_mode": "HTML"
                }
                resp = requests.post(f"{self.api_url}/sendDocument", json=payload, timeout=30)
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram document: {e}")
            return {}

    def send_video(self, video_path_or_url: str, caption: Optional[str] = None, chat_id: Optional[str] = None) -> dict:
        """Send an MP4 video to Telegram with native streaming/HD playback support."""
        if not self.token:
            return {}
        chat_id = chat_id or self.default_chat_id
        clean_caption = (caption or "").replace("**", "").replace("*", "")

        try:
            if os.path.exists(video_path_or_url):
                with open(video_path_or_url, "rb") as f:
                    data = {
                        "chat_id": chat_id,
                        "caption": clean_caption,
                        "parse_mode": "HTML",
                        "supports_streaming": True
                    }
                    resp = requests.post(f"{self.api_url}/sendVideo", data=data, files={"video": f}, timeout=60)
                    return resp.json()
            else:
                payload = {
                    "chat_id": chat_id,
                    "video": video_path_or_url,
                    "caption": clean_caption,
                    "parse_mode": "HTML",
                    "supports_streaming": True
                }
                resp = requests.post(f"{self.api_url}/sendVideo", json=payload, timeout=30)
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram video: {e}")
            return {}

    def download_file(self, file_id: str, dest_path: str) -> Optional[str]:
        """Download a photo/document from Telegram given its file_id."""
        if not self.token:
            return None
        try:
            file_info_resp = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id}, timeout=20)
            file_info = file_info_resp.json()
            if not file_info.get("ok"):
                logger.error(f"Failed to get file info: {file_info}")
                return None
            
            file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
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

    def send_post_approval_card(self, post_id: int, topic: str, hook_formula: str, draft_text: str, image_url: Optional[str] = None, chat_id: Optional[str] = None):
        """Send an interactive post approval card with inline action buttons and optional visual."""
        escaped_topic = _esc(topic)
        escaped_formula = _esc(hook_formula)
        escaped_draft = _esc(draft_text)

        download_url = None
        if image_url:
            filename = os.path.basename(image_url)
            mp4_path = str(Path(image_url).with_suffix(".mp4"))

            if os.path.exists(mp4_path):
                # 1. Send 1080p High-Definition MP4 Video (TrueColor 16.7M colors, crystal-sharp typography)
                self.send_video(
                    mp4_path,
                    caption=(
                        f"🎬 <b>1080p HD Architecture Motion (Post #{post_id})</b>\n"
                        f"📌 <i>{escaped_topic}</i>\n"
                        f"✨ TrueColor 60fps | Tap to play in crystal clarity"
                    ),
                    chat_id=chat_id
                )
            elif str(image_url).lower().endswith(".gif"):
                self.send_animation(
                    image_url,
                    caption=f"🎬 <b>Animated Architecture for Post #{post_id}</b>\n📌 <i>{escaped_topic}</i>",
                    chat_id=chat_id
                )
            else:
                self.send_photo(
                    image_url,
                    caption=f"🎨 <b>Architecture Diagram for Post #{post_id}</b>\n📌 <i>{escaped_topic}</i>",
                    chat_id=chat_id
                )

            # 2. Deliver the uncompressed raw master document with direct web download link
            doc_resp = self.send_document(
                image_url,
                caption=(
                    f"📁 <b>Master High-Resolution GIF (Raw Uncompressed)</b>\n"
                    f"📌 Post #{post_id} | 2800x1600 Retina Architecture Poster\n"
                    f"👉 Download from Telegram file above or use the web link below."
                ),
                chat_id=chat_id
            )

            file_id = None
            if isinstance(doc_resp, dict) and doc_resp.get("ok"):
                file_id = doc_resp.get("result", {}).get("document", {}).get("file_id")

            render_base = os.getenv("RENDER_EXTERNAL_URL", "https://buxbi.onrender.com").rstrip("/")
            if file_id:
                # Durable link proxying Telegram's CDN via Render (works even after Render restart/redeploy)
                download_url = f"{render_base}/dl/{file_id}/{filename}"
            else:
                download_url = f"{render_base}/media/gifs/{filename}"

        char_count = len(draft_text)
        dl_section = ""
        if download_url:
            dl_section = (
                f"\n📥 <b>Master High-Resolution GIF:</b>\n"
                f"🔗 <a href=\"{download_url}\">Click here to Download Master GIF</a>\n"
                f"<i>💡 Download to review or edit, then send it back to BuxBi right here in chat to combine with this post!</i>\n"
            )
        
        message_html = (
            f"<b>🚀 NEW GEN AI LINKEDIN POST DRAFT</b>\n\n"
            f"<b>📌 Topic:</b> {escaped_topic}\n"
            f"<b>🎯 Hook Formula:</b> <code>{escaped_formula}</code>\n"
            f"<b>📊 Length:</b> {char_count} chars (sweet spot: 900-1,300)\n\n"
            f"<b>--- Post Preview ---</b>\n\n"
            f"{escaped_draft}\n\n"
            f"<b>---------------------</b>\n"
            f"{dl_section}\n"
            f"<i>Tap an option below to manage this post:</i>"
        )

        inline_keyboard_rows = [
            [
                {"text": "🚀 Approve & Post Now", "callback_data": f"approve_now:{post_id}"},
                {"text": "📅 Schedule (08:30)", "callback_data": f"schedule_slot:{post_id}"}
            ]
        ]
        if download_url:
            inline_keyboard_rows.append([
                {"text": "📥 Download Master GIF (Web Link)", "url": download_url}
            ])
        inline_keyboard_rows.extend([
            [
                {"text": "🎨 Edit GIF Style", "callback_data": f"edit_gif:{post_id}"},
                {"text": "📸 Upload Photo", "callback_data": f"upload_image:{post_id}"}
            ],
            [
                {"text": "🔄 Regenerate Angle", "callback_data": f"regen_post:{post_id}"},
                {"text": "🤝 Get 3 Leads", "callback_data": f"send_leads:{post_id}"}
            ],
            [
                {"text": "❌ Discard", "callback_data": f"discard_post:{post_id}"}
            ]
        ])

        inline_keyboard = {"inline_keyboard": inline_keyboard_rows}

        return self.send_message(message_html, reply_markup=inline_keyboard, chat_id=chat_id)

    def send_gif_customization_menu(self, post_id: int, current_theme: str = "Champagne & Bronze (5)", current_size: str = "Poster (1400x800)", chat_id: Optional[str] = None):
        """Send interactive menu to choose one of 3 authentic themes and canvas resolutions."""
        message_html = (
            f"<b>🎨 CUSTOMIZE ARCHITECTURAL GIF (Post #{post_id})</b>\n\n"
            f"• <b>Active Theme:</b> {current_theme}\n"
            f"• <b>Active Resolution:</b> {current_size}\n\n"
            "<i>Select a theme or canvas size below to immediately re-render the animation:</i>"
        )
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏆 Champagne & Bronze (5)", "callback_data": f"gif_theme:5:{post_id}"},
                    {"text": "⚡ Graphite & Blue (6)", "callback_data": f"gif_theme:6:{post_id}"}
                ],
                [
                    {"text": "🔮 Royal Amethyst (4)", "callback_data": f"gif_theme:4:{post_id}"}
                ],
                [
                    {"text": "🖼 Poster (1400x800 - Default)", "callback_data": f"gif_size:poster:{post_id}"},
                    {"text": "🖥 Landscape (1200x630)", "callback_data": f"gif_size:landscape:{post_id}"}
                ],
                [
                    {"text": "📱 Portrait (1080x1350)", "callback_data": f"gif_size:portrait:{post_id}"},
                    {"text": "⬛ Square (1080x1080)", "callback_data": f"gif_size:square:{post_id}"}
                ],
                [
                    {"text": "⬅️ Back to Post Draft", "callback_data": f"back_to_draft:{post_id}"}
                ]
            ]
        }
        return self.send_message(message_html, reply_markup=inline_keyboard, chat_id=chat_id)

    def send_weekly_intimation(self, chat_id: Optional[str] = None):
        """Send proactive weekly prompt to Madan requesting new documents, technologies, or insights."""
        msg = (
            "🧠 <b>BUXBI WEEKLY KNOWLEDGE REFRESH</b>\n\n"
            "Hey Madan! To ensure our daily LinkedIn content stays unmatched in technical depth and strictly ahead of the curve, "
            "what new technologies, frameworks, or production lessons should we master this week?\n\n"
            "<b>How you can feed me new insights:</b>\n"
            "• <b>Send a document:</b> Drop any PDF whitepaper, Markdown (.md), or text (.txt) file directly in this chat.\n"
            "• <b>Send technology names:</b> Type e.g. <code>/learn Moonshine STT, vLLM chunked prefill, BitNet b1.58</code>.\n"
            "• <b>Send production notes:</b> Share real bugs, memory bottlenecks, or latency numbers you ran into.\n\n"
            "<i>I will ingest the data, research external technical sources, analyze the mechanics, and craft this week's posts and animated architectural GIFs around them!</i>"
        )
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📚 View Knowledge Vault", "callback_data": "view_vault:0"},
                    {"text": "🚀 Draft Today's Post", "callback_data": "draft_new:0"}
                ]
            ]
        }
        return self.send_message(msg, reply_markup=inline_keyboard, chat_id=chat_id)


    def send_final_confirmation_card(
        self,
        post_id: int,
        topic: str,
        draft_text: str,
        image_url: str,
        theme_name: Optional[str] = None,
        chat_id: Optional[str] = None,
        public_media_url: Optional[str] = None,
        telegram_file_id: Optional[str] = None,
        media_kind: Optional[str] = None,
        **kwargs
    ):
        """Send preview of post with attached image/video/GIF and ask for final confirmation before posting."""
        escaped_topic = _esc(topic)
        escaped_draft = _esc(draft_text)
        theme_caption = f"\n🎨 <b>Theme:</b> {_esc(theme_name)}" if theme_name else ""
        caption = (
            f"🖼 <b>Post Preview with Your Attached Media</b>{theme_caption}\n"
            f"📌 <b>Topic:</b> {escaped_topic}\n\n"
            f"✨ Attached: <code>{os.path.basename(image_url)}</code>\n"
            f"Ready to publish to LinkedIn!"
        )

        ext = os.path.splitext(image_url)[1].lower()
        if ext in (".mp4", ".mov") or media_kind in ("animation", "video"):
            try:
                if ext == ".mp4" and media_kind != "animation":
                    self.send_video(image_url, caption=caption, chat_id=chat_id)
                else:
                    self.send_animation(image_url, caption=caption, chat_id=chat_id)
            except Exception:
                self.send_document(image_url, caption=caption, chat_id=chat_id)
        elif ext == ".gif":
            self.send_animation(image_url, caption=caption, chat_id=chat_id)
        else:
            self.send_photo(image_url, caption=caption, chat_id=chat_id)

        media_line = f"\n🌐 <b>Public Media URL:</b> <a href=\"{public_media_url}\">View Online</a>\n" if public_media_url else ""
        message_html = (
            f"<b>📋 Final Combined Post for Post #{post_id}</b>\n\n"
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
                                  profile_url: str, why_relevant: str, note: str, chat_id: Optional[str] = None):
        """Send a high-authority connection lead with 1-click profile link and copyable note."""
        escaped_name = _esc(name)
        escaped_title = _esc(title)
        escaped_company = _esc(company)
        escaped_why = _esc(why_relevant)
        escaped_note = _esc(note)
        
        message_html = (
            f"<b>🤝 HIGH-AUTHORITY GEN AI CONNECTION LEAD</b>\n\n"
            f"<b>👤 Name:</b> {escaped_name}\n"
            f"<b>💼 Title:</b> {escaped_title} ({escaped_company})\n"
            f"<b>🔗 Profile:</b> <a href=\"{profile_url}\">{profile_url}</a>\n"
            f"<b>💡 Why Connect:</b> {escaped_why}\n\n"
            f"<b>📝 Personalized Note ({len(note)}/300 chars):</b>\n"
            f"<pre>{escaped_note}</pre>\n\n"
            f"👉 <i>Open the profile link, click 'Connect' then 'Add a note', and paste the text above!</i>"
        )

        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🔗 Open {name}'s LinkedIn Profile", "url": profile_url}
                ]
            ]
        }

        return self.send_message(message_html, reply_markup=inline_keyboard, chat_id=chat_id)

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
