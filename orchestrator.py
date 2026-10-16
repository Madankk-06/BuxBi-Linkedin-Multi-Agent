import re
import time
import logging
import threading
from typing import Optional
from agents.trend_scout import trend_scout
from agents.domain_director import domain_director
from agents.post_architect import post_architect
from agents.humanizer import humanizer
from agents.authority_networker import authority_networker
from agents.image_architect import image_architect
from agents.repurposer import repurposer
from lib.telegram_bot import telegram_bot
from lib.publora_client import publora_client
from core.database import db

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self):
        self.pending_image_upload_post_id: Optional[int] = None

    def run_morning_content_pipeline(self) -> int:
        """Autonomous pipeline: Select diverse Gen AI domain -> Draft practitioner post -> Humanize -> Telegram."""
        logger.info("Executing Autonomous Content Pipeline with Domain Director...")
        
        # 1. Select diverse, high-impact Gen AI domain topic
        brief = domain_director.select_topic_brief()
        topic_title = f"{brief['domain_name']}: {brief['concept']}"
        logger.info(f"Selected Domain: {brief['domain_name']} | Concept: {brief['concept']}")
        
        # 2. Draft practitioner-style post
        formula, raw_draft = post_architect.draft_post(brief)
        
        # 3. Aggressive humanizer pass
        final_draft = humanizer.audit_and_humanize(raw_draft)
        
        # 4. Automatic image generation disabled (user provides custom visual via Telegram)
        image_path = None

        # 5. Save to Database
        post_id = db.save_post_draft(topic_title, formula, final_draft, image_url=image_path)
        logger.info(f"Saved post draft #{post_id} to database.")
        
        # 6. Send Interactive Approval Card to Telegram
        telegram_bot.send_post_approval_card(
            post_id=post_id,
            topic=topic_title,
            hook_formula=formula,
            draft_text=final_draft,
            image_url=image_path
        )
        logger.info(f"Sent approval card for post #{post_id} to Telegram.")
        return post_id

    def run_repurpose_pipeline(self, raw_input: str, chat_id: Optional[str] = None) -> int:
        """Autonomous pipeline: Repurpose cross-platform content/URL -> Structure & Humanize -> Telegram Approval."""
        logger.info("Executing Autonomous Repurpose Pipeline...")
        telegram_bot.send_message("🔄 Repurposing your content into a high-authority LinkedIn post...", chat_id=chat_id)
        topic_title, formula, final_draft = repurposer.repurpose(raw_input)
        post_id = db.save_post_draft(topic_title, formula, final_draft, image_url=None)
        logger.info(f"Saved repurposed post #{post_id} to database.")
        telegram_bot.send_post_approval_card(
            post_id=post_id,
            topic=topic_title,
            hook_formula=formula,
            draft_text=final_draft,
            image_url=None
        )
        logger.info(f"Sent approval card for repurposed post #{post_id} to Telegram.")
        return post_id

    def run_networking_pipeline(self, count: int = 3):
        """Autonomous pipeline: Find high-authority Gen AI leaders -> Draft notes -> Send to Telegram."""
        logger.info("Executing Autonomous Networking Pipeline...")
        leads = authority_networker.generate_daily_leads(count=count)
        
        for lead in leads:
            telegram_bot.send_connection_lead_card(
                lead_id=0,
                name=lead["name"],
                title=lead["title"],
                company=lead["company"],
                profile_url=lead["profile_url"],
                why_relevant=lead["why_relevant"],
                note=lead["customized_note"]
            )
        logger.info(f"Sent {len(leads)} connection leads to Telegram.")

    def _reconstruct_post_from_message(self, message_obj: Optional[dict]) -> Optional[dict]:
        """Recover post draft text and media URL directly from a Telegram message if container restarted."""
        if not message_obj or "text" not in message_obj:
            return None
        raw_text = message_obj["text"]
        topic = "Recovered LinkedIn Draft"
        media_url = None

        # Extract Media URL if present
        media_match = re.search(r"Media URL:\s*(https?://\S+)", raw_text)
        if media_match:
            media_url = media_match.group(1).strip()

        # Case 1: Initial approval card ("--- Post Preview --- ... ---------------------")
        if "--- Post Preview ---" in raw_text and "---------------------" in raw_text:
            topic_match = re.search(r"Topic:\s*(.+)", raw_text)
            if topic_match:
                topic = topic_match.group(1).strip()
            draft_part = raw_text.split("--- Post Preview ---", 1)[1].split("---------------------", 1)[0].strip()
            if draft_part:
                new_id = db.save_post_draft(topic, "Recovered", draft_part, image_url=media_url)
                return db.get_post(new_id)

        # Case 2: Final confirmation card ("📋 Final Post Draft for Post #X ... Tap below to confirm and post:")
        if "Final Post Draft for Post" in raw_text and "Tap below to confirm" in raw_text:
            body = re.sub(r"^.*?Final Post Draft for Post #\d+\s*", "", raw_text, flags=re.DOTALL)
            body = re.sub(r"\s*🖼\s*Media URL:\s*https?://\S+", "", body)
            body = re.sub(r"\s*Tap below to confirm.*$", "", body, flags=re.DOTALL).strip()
            if body:
                new_id = db.save_post_draft(topic, "Recovered", body, image_url=media_url)
                return db.get_post(new_id)

        return None

    def _verify_live_publication(self, post_id: int, post_group_id: str, chat_id: str):
        """Background verifier: polls Publora after ~65s to confirm the post transitioned from 'scheduled' to 'published' on LinkedIn."""
        def _poll():
            time.sleep(65)
            for attempt in range(5):
                status_data = publora_client.get_post_status(post_group_id)
                group = status_data.get("postGroup") or status_data
                status = group.get("status")
                logger.info(f"Publora verification poll #{attempt+1} for {post_group_id}: status={status}")

                if status in ("published", "partially_published"):
                    telegram_bot.send_message(
                        f"🎉 <b>VERIFIED LIVE ON LINKEDIN!</b>\n\n"
                        f"✅ Post #{post_id} (<code>{post_group_id}</code>) is now officially published on your LinkedIn feed.\n"
                        f"🔗 <a href='https://www.linkedin.com/in/madankk04122004/recent-activity/all/'>View Live Activity on LinkedIn</a>",
                        chat_id=chat_id
                    )
                    return

                if status in ("failed", "error"):
                    err_detail = group.get("error") or str(group)
                    telegram_bot.send_message(
                        f"⚠️ <b>Publora Dispatch Alert for Post #{post_id}:</b>\n"
                        f"Status reported: <code>{status}</code>\n"
                        f"Details: {err_detail}",
                        chat_id=chat_id
                    )
                    return

                time.sleep(20)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    def _publish_post_now(self, post: dict, chat_id: str) -> bool:
        """Publish a post immediately via Publora (schedules 60s out in UTC ISO-8601 and verifies live status)."""
        post_id = post["id"]
        db.update_post_status(post_id, "approved")

        if publora_client.is_configured:
            res = publora_client.publish_or_schedule_post(
                post["draft_text"],
                scheduled_time=None,
                image_path=post.get("image_url")
            )
            if res.get("success"):
                publora_id = res.get("post_id", "")
                sched_utc = res.get("scheduled_time_utc", "")
                media_note = f"\n🖼 <b>Attached Media:</b> Included" if res.get("media_url") else ""
                db.update_post_status(post_id, "approved", scheduled_time=sched_utc, post_urn=str(publora_id))
                msg = (
                    f"🚀 <b>Post #{post_id} Queued for Immediate Live Publishing!</b>\n\n"
                    f"🆔 <b>Publora ID:</b> <code>{publora_id}</code>\n"
                    f"⏱ <b>Dispatch Time:</b> <code>{sched_utc}</code> (~60 seconds){media_note}\n\n"
                    f"<i>Publora is dispatching your post to LinkedIn now. I will send you a confirmation alert in ~60 seconds once LinkedIn marks it LIVE!</i>\n"
                    f"🔗 <a href='https://www.linkedin.com/in/madankk04122004/recent-activity/all/'>Open LinkedIn Activity</a>"
                )
                telegram_bot.send_message(msg, chat_id=chat_id)
                if publora_id:
                    self._verify_live_publication(post_id, str(publora_id), chat_id)
                return True
            else:
                msg = f"⚠️ <b>Publora Publishing Error:</b> {res.get('error')}"
                telegram_bot.send_message(msg, chat_id=chat_id)
                return False
        else:
            msg = (
                f"✅ <b>Post #{post_id} Approved!</b>\n\n"
                f"<i>Copy and paste directly to LinkedIn:</i>\n\n"
                f"<pre>{post['draft_text']}</pre>"
            )
            telegram_bot.send_message(msg, chat_id=chat_id)
            return True

    def handle_callback_action(self, callback_data: str, chat_id: str, message_id: int, message_obj: Optional[dict] = None):
        """Handle button clicks from Telegram."""
        action, post_id_str = callback_data.split(":")
        post_id = int(post_id_str)
        post = db.get_post(post_id)

        if not post and message_obj:
            post = self._reconstruct_post_from_message(message_obj)
            if post:
                post_id = post["id"]

        if not post:
            telegram_bot.send_message(
                "❌ Post draft was not found in the container database (container may have restarted). "
                "Type <b>'draft post'</b> to generate a fresh draft!",
                chat_id=chat_id
            )
            return

        if action == "generate_flux":
            from lib.flux_client import flux_engine
            telegram_bot.send_message(f"🎨 Generating a tailored FLUX.1 visual for Post #{post_id}...", chat_id=chat_id)
            try:
                img_path, theme_name = flux_engine.generate_image_for_post(
                    post_id=post_id,
                    topic=post["topic"],
                    draft_text=post["draft_text"]
                )
                public_url = publora_client.upload_local_media(img_path)
                db.update_post_image(post_id, public_url or img_path)
                telegram_bot.send_final_confirmation_card(
                    post_id=post_id,
                    topic=post["topic"],
                    draft_text=post["draft_text"],
                    image_url=img_path,
                    theme_name=theme_name,
                    chat_id=chat_id,
                    public_media_url=public_url
                )
                telegram_bot.edit_message_reply_markup(chat_id, message_id)
            except Exception as e:
                logger.error(f"Error generating FLUX visual: {e}")
                telegram_bot.send_message(f"⚠️ Could not generate image: {e}. You can tap 'Add Custom Image' to send your own!", chat_id=chat_id)
            return

        elif action == "upload_image":
            self.pending_image_upload_post_id = post_id
            msg = (
                f"📸 <b>Awaiting Your Custom Image for Post #{post_id}!</b>\n\n"
                f"Please send or drop your photo/graphic (JPG, PNG, or GIF) right here in the chat.\n"
                f"I will attach it to your post content and ask for your final confirmation before posting!"
            )
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action in ("confirm_post", "approve_now"):
            ok = self._publish_post_now(post, chat_id)
            if ok:
                telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "schedule_slot":
            if publora_client.is_configured:
                res = publora_client.publish_or_schedule_post(
                    post["draft_text"],
                    scheduled_time="08:30",
                    image_path=post.get("image_url")
                )
                if res.get("success"):
                    publora_id = res.get("post_id", "")
                    sched_utc = res.get("scheduled_time_utc", "08:30 IST")
                    db.update_post_status(post_id, "scheduled", scheduled_time=sched_utc, post_urn=str(publora_id))
                    msg = (
                        f"📅 <b>Post #{post_id} Scheduled on Publora for 08:30 AM IST!</b>\n"
                        f"🆔 <b>Publora ID:</b> <code>{publora_id}</code>\n"
                        f"🕒 <b>UTC Slot:</b> <code>{sched_utc}</code>"
                    )
                else:
                    msg = f"⚠️ Could not schedule on Publora: {res.get('error')}"
            else:
                db.update_post_status(post_id, "scheduled", scheduled_time="08:30")
                msg = f"📅 <b>Post #{post_id} Scheduled for 08:30 AM!</b>"
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)

        elif action == "regen_post":
            telegram_bot.send_message(f"🔄 Regenerating angle for Post #{post_id}...", chat_id=chat_id)
            self.run_morning_content_pipeline()

        elif action == "discard_post":
            db.update_post_status(post_id, "discarded")
            telegram_bot.send_message(f"🗑️ Post #{post_id} has been discarded.", chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)

    def handle_user_image(self, file_id: str, chat_id: str):
        """Receive a custom image sent by the user in Telegram, upload to public HTTPS host, attach it, and ask for confirmation."""
        target_post = None
        if self.pending_image_upload_post_id:
            target_post = db.get_post(self.pending_image_upload_post_id)
            
        if not target_post:
            target_post = db.get_latest_pending_post() or db.get_latest_post()
            
        if not target_post:
            telegram_bot.send_message(
                "📸 I received your image! However, there is no pending post draft right now. "
                "Type <b>'draft post'</b> to generate a new post draft first!",
                chat_id=chat_id
            )
            return

        post_id = target_post["id"]
        dest_path = f"data/user_uploads/post_{post_id}_{int(time.time())}.jpg"
        downloaded = telegram_bot.download_file(file_id, dest_path)
        
        if downloaded:
            # Upload immediately to public HTTPS URL so Publora can ingest it and URL persists in Telegram
            public_url = publora_client.upload_local_media(downloaded)
            stored_image_ref = public_url or downloaded
            db.update_post_image(post_id, stored_image_ref)
            self.pending_image_upload_post_id = None
            # Show preview with the image and request confirmation
            telegram_bot.send_final_confirmation_card(
                post_id=post_id,
                topic=target_post["topic"],
                draft_text=target_post["draft_text"],
                image_url=downloaded,
                chat_id=chat_id,
                public_media_url=public_url
            )
        else:
            telegram_bot.send_message("⚠️ Could not download the image. Please try sending it again.", chat_id=chat_id)

    def handle_conversational_text(self, text: str, chat_id: str, message_obj: Optional[dict] = None):
        """Handle conversational commands, questions, and instructions from the user in Telegram."""
        from lib.llm_client import llm_client
        clean_text = text.strip().lower()

        # 1. Quick command intents ("post now", "publish", "approve")
        if clean_text in ["post now", "publish", "approve", "approve now", "retry", "retry post"]:
            target_post = None
            if message_obj and "reply_to_message" in message_obj:
                target_post = self._reconstruct_post_from_message(message_obj["reply_to_message"])
            if not target_post:
                target_post = db.get_latest_pending_post() or db.get_latest_post()

            if target_post:
                self._publish_post_now(target_post, chat_id)
            else:
                telegram_bot.send_message(
                    "ℹ️ No post draft found in database. Reply <b>'post now'</b> directly to a draft message in Telegram, or type <b>'draft post'</b> to create a new one!",
                    chat_id=chat_id
                )
            return

        if any(trigger in clean_text for trigger in ["draft post", "create post", "generate post", "new post", "write a post"]):
            telegram_bot.send_message("🔍 Scouting trends & drafting your next Gen AI architecture post...", chat_id=chat_id)
            self.run_morning_content_pipeline()
            return

        if any(trigger in clean_text for trigger in ["find leaders", "connections", "network", "scout leaders"]):
            telegram_bot.send_message("🤝 Sourcing top Gen AI authorities & crafting bespoke connection notes...", chat_id=chat_id)
            self.run_networking_pipeline(count=3)
            return

        if clean_text.startswith(("/repurpose", "repurpose")):
            content_to_repurpose = re.sub(r'^(?:/repurpose|repurpose)[:\s]*', '', text, flags=re.IGNORECASE).strip()
            if not content_to_repurpose:
                telegram_bot.send_message(
                    "ℹ️ <b>How to use Repurpose:</b>\n\n"
                    "Send: <code>/repurpose &lt;URL or notes/text&gt;</code>\n\n"
                    "For example:\n"
                    "• <code>/repurpose https://arxiv.org/abs/...</code>\n"
                    "• <code>/repurpose We overhauled our RAG architecture today with hybrid search and cross-encoders...</code>",
                    chat_id=chat_id
                )
                return
            self.run_repurpose_pipeline(content_to_repurpose, chat_id=chat_id)
            return

        if clean_text in ["status", "/status"]:
            pending = db.get_latest_pending_post() or db.get_latest_post()
            pending_info = f"Post #{pending['id']} [{pending['status']}] ('{pending['topic'][:35]}...')" if pending else "None"
            status_text = (
                "<b>🟢 BuxBi Status: ACTIVE & 24/7 MONITORING</b>\n\n"
                f"• <b>Latest Draft:</b> {pending_info}\n"
                f"• <b>Active Skills:</b> Post Writer, Humanizer, Content Planner, Repurposer (/repurpose)\n"
                f"• <b>Publishing Engine:</b> Publora Live Dispatch (60s UTC ISO-8601 + Auto-Verification)\n"
                f"• <b>LLM:</b> Groq (qwen/qwen3.8-27b)\n"
                f"• <b>Cloud Status:</b> Dual DB (SQLite/MySQL) + HTTP Healthcheck Server (port 10000)\n\n"
                "<i>Commands: /status, /repurpose &lt;url/text&gt;, 'draft post', 'network', 'post now'</i>"
            )
            telegram_bot.send_message(status_text, chat_id=chat_id)
            return

        # 2. Conversational response via Groq
        system_prompt = """
You are Buxbi (also known as LinkBi), a sharp, helpful, and technically brilliant executive AI assistant for LinkedIn growth and Generative AI thought leadership.
You are chatting directly with your creator and user, Madan, via Telegram.

GUIDELINES:
1. Tone: Friendly, concise, highly competent, professional senior AI engineer/partner.
2. Address him naturally as Madan when appropriate.
3. Keep answers concise (1-3 short paragraphs, formatted with clear spacing or bullet points), perfectly suited for mobile Telegram reading.
4. If he asks about technical concepts (like vector indexing, RAG layers, Step 4 & 5, or prompting), explain them clearly and authoritatively.
5. If he asks you to perform an action (e.g. generate a post or check something), confirm and guide him.
"""
        try:
            bot_reply = llm_client.generate(text, system_prompt=system_prompt, temperature=0.7)
            telegram_bot.send_message(bot_reply, chat_id=chat_id)
        except Exception as e:
            logger.error(f"Error generating conversational reply: {e}")
            telegram_bot.send_message("I hear you, Madan! How can I assist you with your LinkedIn presence or posts right now?", chat_id=chat_id)

orchestrator = AgentOrchestrator()
