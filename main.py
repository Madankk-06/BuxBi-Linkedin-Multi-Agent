import time
import logging
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import os
import threading
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

from core.config import config
from core.database import db
from lib.telegram_bot import telegram_bot
from orchestrator import orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("LinkedinAgentMain")

class HealthHandler(BaseHTTPRequestHandler):
    MIME_MAP = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "mp4": "video/mp4"
    }

    def _serve_telegram_file(self):
        """Stream a file stored on Telegram servers: /dl/<file_id>/<filename>.

        Telegram is the durable storage here, so the link keeps working even after
        Render restarts/redeploys wipe the local disk.
        """
        from urllib.parse import unquote
        parts = self.path.split("?", 1)[0][len("/dl/"):].split("/")
        file_id = unquote(parts[0]) if parts and parts[0] else ""
        filename = os.path.basename(unquote(parts[1])) if len(parts) > 1 and parts[1] else "buxbi_media.gif"
        if not file_id or not config.TELEGRAM_BOT_TOKEN:
            self.send_response(404)
            self.end_headers()
            return
        try:
            api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
            info = requests.get(f"{api}/getFile", params={"file_id": file_id}, timeout=20).json()
            if not info.get("ok"):
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"File not found or expired on Telegram.")
                return
            tg_path = info["result"]["file_path"]
            dl = requests.get(f"https://api.telegram.org/file/bot{config.TELEGRAM_BOT_TOKEN}/{tg_path}", timeout=60)
            if dl.status_code != 200:
                self.send_response(502)
                self.end_headers()
                return
            data = dl.content
            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "gif"
            self.send_response(200)
            self.send_header("Content-type", self.MIME_MAP.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            logger.error(f"Telegram file proxy failed: {e}")
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        if self.path.startswith("/dl/"):
            self._serve_telegram_file()
            return

        if self.path.startswith("/media/"):
            rel_path = self.path.split("?", 1)[0][len("/media/"):]
            if rel_path.startswith("gifs/"):
                filename = os.path.basename(rel_path[len("gifs/"):])
                filepath = os.path.join("data", "generated_gifs", filename)
            else:
                filename = os.path.basename(rel_path)
                filepath = os.path.join("data", "user_uploads", filename)
                if not os.path.exists(filepath):
                    filepath = os.path.join("data", "generated_gifs", filename)

            if os.path.exists(filepath) and os.path.isfile(filepath):
                ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "jpg"
                self.send_response(200)
                self.send_header("Content-type", self.MIME_MAP.get(ext, "application/octet-stream"))
                self.send_header("Content-Disposition", f'inline; filename="{filename}"')
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"healthy","agent":"Buxbi","uptime":"24/7"}')

    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.getenv("PORT", 10000))
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Healthcheck HTTP server active on port {port}")
    except Exception as e:
        logger.warning(f"Could not bind health port {port}: {e}")

def run_daily_job():
    """Triggered every day at the scheduled time."""
    logger.info("Executing scheduled morning agent job...")
    try:
        orchestrator.run_morning_content_pipeline()
        orchestrator.run_networking_pipeline(count=config.MAX_DAILY_CONNECTIONS)
    except Exception as e:
        logger.error(f"Error during scheduled job: {e}")
        telegram_bot.send_message(f"⚠️ Error running autonomous scheduled job: {e}")

def run_weekly_intimation_job():
    """Triggered weekly (every Sunday evening) to request new tech insights, documents, or focus areas."""
    logger.info("Executing scheduled weekly knowledge intimation...")
    try:
        telegram_bot.send_weekly_intimation()
    except Exception as e:
        logger.error(f"Error sending weekly intimation: {e}")

def poll_telegram_updates():
    """Long-polling listener for Telegram commands and inline button callbacks."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured. Telegram polling is disabled.")
        return

    logger.info("Starting Telegram Bot listener...")
    offset = None
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    # 1. Handle inline button callbacks
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        data_payload = cb.get("data", "")
                        msg_obj = cb.get("message", {})
                        chat_id = str(msg_obj["chat"]["id"])
                        message_id = msg_obj["message_id"]
                        
                        telegram_bot.answer_callback_query(cb_id, "Processing your choice...")
                        orchestrator.handle_callback_action(data_payload, chat_id, message_id, message_obj=msg_obj)

                    # 2. Handle photos sent by user
                    elif "message" in update and "photo" in update["message"]:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        # Get highest resolution photo
                        photo_file_id = msg["photo"][-1]["file_id"]
                        orchestrator.handle_user_image(photo_file_id, chat_id, media_kind="photo", reply_msg=msg.get("reply_to_message"))

                    # 2b. Handle GIFs (Telegram delivers them as 'animation') sent back by the user
                    elif "message" in update and "animation" in update["message"]:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        anim = msg["animation"]
                        orchestrator.handle_user_image(
                            anim["file_id"], chat_id, media_kind="animation",
                            file_name=anim.get("file_name"), mime_type=anim.get("mime_type"),
                            reply_msg=msg.get("reply_to_message")
                        )

                    # 2c. Handle MP4 videos sent back by the user
                    elif "message" in update and "video" in update["message"]:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        vid = msg["video"]
                        orchestrator.handle_user_image(
                            vid["file_id"], chat_id, media_kind="video",
                            file_name=vid.get("file_name"), mime_type=vid.get("mime_type"),
                            reply_msg=msg.get("reply_to_message")
                        )

                    # 3. Handle images or technical documents sent by user
                    elif "message" in update and "document" in update["message"]:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        doc = msg["document"]
                        mime = doc.get("mime_type", "")
                        file_name = doc.get("file_name", "document.txt")
                        if mime.startswith("image/") or mime.startswith("video/"):
                            orchestrator.handle_user_image(
                                doc["file_id"], chat_id, media_kind="document",
                                file_name=file_name, mime_type=mime,
                                reply_msg=msg.get("reply_to_message")
                            )
                        else:
                            orchestrator.handle_user_document(doc["file_id"], file_name, chat_id)

                    # 4. Handle text commands and conversation
                    elif "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        text = msg["text"].strip()
                        chat_id = str(msg["chat"]["id"])

                        if text == "/start" or text == "/help":
                            help_text = (
                                "👋 <b>Hey Madan! I'm Buxbi, your autonomous LinkedIn Gen AI partner.</b>\n\n"
                                "Here is what we can do together:\n"
                                "• <b>Chat with me:</b> Ask me any question, tell me what to post about, or give me feedback!\n"
                                "• <b>Send an image:</b> Send me any photo/GIF directly here, and I'll attach it to your current post draft.\n"
                                "• <b>Text commands:</b> Type <code>draft post</code>, <code>post now</code>, <code>/repurpose &lt;url/text&gt;</code>, <code>find leaders</code>, or <code>status</code>.\n"
                                "• <b>Buttons:</b> Tap the buttons below any post card to approve, schedule, or regenerate."
                            )
                            telegram_bot.send_message(help_text, chat_id=chat_id)
                        else:
                            orchestrator.handle_conversational_text(text, chat_id, message_obj=msg)

            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            time.sleep(5)

def main():
    logger.info("Initializing LinkedIn Gen AI Autonomous Multi-Agent System...")
    
    missing = config.validate()
    if missing:
        logger.warning(f"Notice: Missing environment variables: {', '.join(missing)}")
        logger.warning("Please update .env to enable full autonomous features.")

    # Start lightweight HTTP healthcheck server for cloud hosting (Render/Koyeb/Railway)
    start_health_server()

    # Setup APScheduler with strict timezone resolution (guarantees Asia/Kolkata 07:30 AM IST)
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(config.TIMEZONE)
    except Exception as e:
        logger.warning(f"Could not load zoneinfo for {config.TIMEZONE} ({e}), falling back...")
        try:
            import pytz
            tz = pytz.timezone(config.TIMEZONE)
        except Exception:
            from datetime import timezone as dt_tz, timedelta
            # Fallback to IST fixed offset (+05:30) if system tz database is missing
            tz = dt_tz(timedelta(hours=5, minutes=30), name="IST")

    scheduler = BackgroundScheduler(timezone=tz)
    hour, minute = config.SCHEDULE_TIME.split(":")
    trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
    daily_job = scheduler.add_job(
        run_daily_job,
        trigger,
        id="daily_linkedin_job",
        replace_existing=True
    )
    # Schedule weekly Sunday 20:00 IST knowledge intimation prompt
    intimation_trigger = CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=tz)
    intimation_job = scheduler.add_job(
        run_weekly_intimation_job,
        intimation_trigger,
        id="weekly_knowledge_intimation_job",
        replace_existing=True
    )
    scheduler.start()
    orchestrator.scheduler = scheduler
    logger.info(f"Daily morning pipeline scheduled strictly for {config.SCHEDULE_TIME} ({config.TIMEZONE}). Next fire: {daily_job.next_run_time}")
    logger.info(f"Weekly Sunday intimation scheduled for 20:00 ({config.TIMEZONE}). Next fire: {intimation_job.next_run_time}")
    # Register 1-click '/' command menu in Telegram
    try:
        telegram_bot.set_bot_commands()
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    # Start Telegram listener in main thread
    poll_telegram_updates()

if __name__ == "__main__":
    main()
