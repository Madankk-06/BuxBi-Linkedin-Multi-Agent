import re
import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional
from agents.trend_scout import trend_scout
from agents.domain_director import domain_director
from agents.post_architect import post_architect
from agents.humanizer import humanizer
from agents.authority_networker import authority_networker
from agents.image_architect import image_architect
from agents.repurposer import repurposer
from core.feedback_memory import feedback_memory
from core.knowledge_vault import knowledge_vault
from lib.gif_engine import gif_engine
from lib.telegram_bot import telegram_bot
from lib.publora_client import publora_client
from core.database import db

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self):
        self.pending_image_upload_post_id: Optional[int] = None

    def run_morning_content_pipeline(self) -> int:
        """Autonomous pipeline: Select diverse Gen AI domain -> Draft practitioner post -> Humanize -> Render Architectural GIF -> Telegram."""
        logger.info("Executing Autonomous Content Pipeline with Domain Director & GIF Engine...")
        
        # 1. Select diverse, high-impact Gen AI domain topic (or user-ingested knowledge)
        brief = domain_director.select_topic_brief()
        topic_title = f"{brief['domain_name']}: {brief['concept']}"
        logger.info(f"Selected Domain: {brief['domain_name']} | Concept: {brief['concept']}")
        telegram_bot.send_message(f"🧠 <b>Drafting Today's Post:</b> {topic_title}\n<i>Pillar: {brief.get('day_pillar', 'Daily Architecture')}</i>")
        
        # 2. Draft practitioner-style post
        formula, raw_draft = post_architect.draft_post(brief)
        
        # 3. Aggressive humanizer pass
        final_draft = humanizer.audit_and_humanize(raw_draft)
        
        # 4. Generate Animated Architectural GIF with deep technical matching content
        image_path = None
        spec_text = ""
        try:
            telegram_bot.send_message("⚙️ <i>Synthesizing deep 5-layer architecture spec & rendering animated GIF...</i>")
            spec_text = gif_engine.design_architecture_spec(topic_title, final_draft)
            out_dir = Path("data/generated_gifs")
            out_dir.mkdir(parents=True, exist_ok=True)
            
            ts = int(time.time())
            temp_gif = str(out_dir / f"temp_{ts}_arch.gif")
            gif_engine.render_gif(spec_text, theme="5", size="poster", output_path=temp_gif, fps=10, duration=4.0)
            image_path = temp_gif
        except Exception as e:
            logger.error(f"Error generating architectural GIF: {e}")
            spec_text = ""
            image_path = None

        # 5. Save to Database
        post_id = db.save_post_draft(topic_title, formula, final_draft, image_url=image_path)
        logger.info(f"Saved post draft #{post_id} to database.")

        if image_path and spec_text:
            final_gif = str(out_dir / f"post_{post_id}_arch.gif")
            final_mp4 = str(out_dir / f"post_{post_id}_arch.mp4")
            temp_mp4 = str(Path(image_path).with_suffix(".mp4"))
            spec_file = str(out_dir / f"post_{post_id}_spec.txt")
            try:
                os.rename(image_path, final_gif)
                if os.path.exists(temp_mp4):
                    os.rename(temp_mp4, final_mp4)
                image_path = final_gif
                db.update_post_image(post_id, final_gif)
            except Exception:
                pass
            try:
                with open(spec_file, "w", encoding="utf-8") as f:
                    f.write(spec_text)
            except Exception as e:
                logger.warning(f"Could not persist spec file: {e}")

        # 6. Send Interactive Approval Card to Telegram with animated GIF
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
        """Autonomous pipeline: Repurpose cross-platform content/URL -> Structure & Humanize -> Render GIF -> Telegram Approval."""
        logger.info("Executing Autonomous Repurpose Pipeline...")
        telegram_bot.send_message("🔄 Repurposing your content into a high-authority LinkedIn post...", chat_id=chat_id)
        topic_title, formula, final_draft = repurposer.repurpose(raw_input)
        
        image_path = None
        spec_text = ""
        try:
            telegram_bot.send_message("⚙️ <i>Synthesizing architectural diagram & animated GIF...</i>", chat_id=chat_id)
            spec_text = gif_engine.design_architecture_spec(topic_title, final_draft)
            out_dir = Path("data/generated_gifs")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            temp_gif = str(out_dir / f"temp_{ts}_arch.gif")
            gif_engine.render_gif(spec_text, theme="5", size="poster", output_path=temp_gif, fps=10, duration=4.0)
            image_path = temp_gif
        except Exception as e:
            logger.error(f"Error generating architectural GIF for repurposed post: {e}")

        post_id = db.save_post_draft(topic_title, formula, final_draft, image_url=image_path)
        logger.info(f"Saved repurposed post #{post_id} to database.")

        if image_path and spec_text:
            final_gif = str(out_dir / f"post_{post_id}_arch.gif")
            final_mp4 = str(out_dir / f"post_{post_id}_arch.mp4")
            temp_mp4 = str(Path(image_path).with_suffix(".mp4"))
            spec_file = str(out_dir / f"post_{post_id}_spec.txt")
            try:
                os.rename(image_path, final_gif)
                if os.path.exists(temp_mp4):
                    os.rename(temp_mp4, final_mp4)
                image_path = final_gif
                db.update_post_image(post_id, final_gif)
            except Exception:
                pass
            try:
                with open(spec_file, "w", encoding="utf-8") as f:
                    f.write(spec_text)
            except Exception:
                pass

        telegram_bot.send_post_approval_card(
            post_id=post_id,
            topic=topic_title,
            hook_formula=formula,
            draft_text=final_draft,
            image_url=image_path,
            chat_id=chat_id
        )
        logger.info(f"Sent approval card for repurposed post #{post_id} to Telegram.")
        return post_id

    def run_networking_pipeline(self, count: int = 3, topic_hint: Optional[str] = None, chat_id: Optional[str] = None):
        """Autonomous pipeline: Find high-authority Gen AI leaders -> Draft notes -> Send to Telegram."""
        logger.info("Executing Autonomous Networking Pipeline...")
        if not topic_hint:
            latest = db.get_latest_pending_post() or db.get_latest_post()
            if latest:
                topic_hint = latest.get("topic")

        leads = authority_networker.generate_daily_leads(count=count, topic_hint=topic_hint)
        
        for lead in leads:
            telegram_bot.send_connection_lead_card(
                lead_id=0,
                name=lead["name"],
                title=lead["title"],
                company=lead["company"],
                profile_url=lead["profile_url"],
                why_relevant=lead["why_relevant"],
                note=lead["customized_note"],
                chat_id=chat_id
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
        parts = callback_data.split(":")
        action = parts[0]
        sub_param = parts[1] if len(parts) >= 3 else None
        post_id_str = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else "0")
        try:
            post_id = int(post_id_str)
        except ValueError:
            post_id = 0

        if action == "view_vault":
            telegram_bot.send_message(knowledge_vault.get_vault_summary(), chat_id=chat_id)
            return

        if action == "draft_new":
            telegram_bot.send_message("🔍 Drafting fresh Gen AI post & architectural GIF...", chat_id=chat_id)
            self.run_morning_content_pipeline()
            return

        post = db.get_post(post_id)

        if not post and message_obj:
            post = self._reconstruct_post_from_message(message_obj)
            if post:
                post_id = post["id"]

        if action == "send_leads":
            telegram_bot.send_message("🤝 Sourcing 3 relevant Gen AI leaders and crafting personalized connection notes...", chat_id=chat_id)
            topic_hint = post.get("topic") if post else None
            self.run_networking_pipeline(count=3, topic_hint=topic_hint, chat_id=chat_id)
            return

        if not post:
            telegram_bot.send_message(
                "❌ Post draft was not found in the container database (container may have restarted). "
                "Type <b>'draft post'</b> to generate a fresh draft!",
                chat_id=chat_id
            )
            return

        # --- GIF CUSTOMIZATION ACTIONS ---
        if action == "edit_gif":
            telegram_bot.send_gif_customization_menu(post_id=post_id, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "gif_theme":
            theme_id = sub_param or "5"
            spec_file = Path(f"data/generated_gifs/post_{post_id}_spec.txt")
            if spec_file.exists():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_text = f.read()
            else:
                spec_text = gif_engine.design_architecture_spec(post["topic"], post["draft_text"])

            telegram_bot.send_message(f"🎨 Re-rendering animated GIF with Theme [{theme_id}]...", chat_id=chat_id)
            ts = int(time.time())
            new_gif_path = f"data/generated_gifs/post_{post_id}_theme_{theme_id}_{ts}.gif"
            gif_engine.render_gif(
                spec_text,
                theme=theme_id,
                size="poster",
                output_path=new_gif_path,
                fps=10,
                duration=4.0
            )
            db.update_post_image(post_id, new_gif_path)
            post["image_url"] = new_gif_path
            telegram_bot.send_post_approval_card(
                post_id=post_id,
                topic=post["topic"],
                hook_formula=post.get("hook_formula", ""),
                draft_text=post["draft_text"],
                image_url=new_gif_path,
                chat_id=chat_id
            )
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "gif_size":
            size_preset = sub_param or "poster"
            spec_file = Path(f"data/generated_gifs/post_{post_id}_spec.txt")
            if spec_file.exists():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_text = f.read()
            else:
                spec_text = gif_engine.design_architecture_spec(post["topic"], post["draft_text"])

            telegram_bot.send_message(f"📐 Re-rendering animated GIF with Canvas Resolution [{size_preset}]...", chat_id=chat_id)
            ts = int(time.time())
            new_gif_path = f"data/generated_gifs/post_{post_id}_{size_preset}_{ts}.gif"
            gif_engine.render_gif(
                spec_text,
                theme="5",
                size=size_preset,
                output_path=new_gif_path,
                fps=10,
                duration=4.0
            )
            db.update_post_image(post_id, new_gif_path)
            post["image_url"] = new_gif_path
            telegram_bot.send_post_approval_card(
                post_id=post_id,
                topic=post["topic"],
                hook_formula=post.get("hook_formula", ""),
                draft_text=post["draft_text"],
                image_url=new_gif_path,
                chat_id=chat_id
            )
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "back_to_draft":
            telegram_bot.send_post_approval_card(
                post_id=post_id,
                topic=post["topic"],
                hook_formula=post.get("hook_formula", ""),
                draft_text=post["draft_text"],
                image_url=post.get("image_url"),
                chat_id=chat_id
            )
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        # --- OTHER BUTTON ACTIONS ---
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

    def handle_user_document(self, file_id: str, file_name: str, chat_id: str):
        """Download and ingest technical whitepapers, text files, or architecture docs into Knowledge Vault."""
        upload_dir = Path("data/user_uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        local_path = str(upload_dir / file_name)

        telegram_bot.send_message(
            f"📥 <b>Receiving Document:</b> <code>{file_name}</code>\n"
            "Analyzing architecture, extracting deep engineering trade-offs, and ingesting into Knowledge Vault...",
            chat_id=chat_id
        )
        saved_path = telegram_bot.download_file(file_id, local_path)
        if not saved_path:
            telegram_bot.send_message("❌ Could not download document from Telegram.", chat_id=chat_id)
            return

        result = knowledge_vault.ingest_document_file(saved_path, file_name)
        if result.get("success"):
            tech_lines = "\n".join([f"• <b>{t}</b>" for t in result.get("added_technologies", [])])
            reply = (
                f"🧠 <b>Document Successfully Ingested into Knowledge Vault!</b>\n\n"
                f"📄 <b>File:</b> {file_name}\n"
                f"🔬 <b>Extracted Technologies ({result.get('added_count')}):</b>\n{tech_lines}\n\n"
                f"💡 <b>Architectural Takeaways:</b>\n{result.get('takeaways')}\n\n"
                f"<i>These concepts are now priority targets for upcoming daily posts and animated GIFs!</i>"
            )
            inline_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🚀 Draft Post on This Now", "callback_data": "draft_new:0"},
                        {"text": "📚 View Knowledge Vault", "callback_data": "view_vault:0"}
                    ]
                ]
            }
            telegram_bot.send_message(reply, reply_markup=inline_keyboard, chat_id=chat_id)
        else:
            telegram_bot.send_message(f"⚠️ Ingestion error: {result.get('error')}", chat_id=chat_id)

    def handle_conversational_text(self, text: str, chat_id: str, message_obj: Optional[dict] = None):

        """Handle conversational commands, questions, and instructions from the user in Telegram."""
        from lib.llm_client import llm_client
        clean_text = text.strip().lower()

        # 1. Quick command intents ("/post", "post now", "publish", "approve")
        if clean_text in ["/post", "post", "post now", "publish", "approve", "approve now", "retry", "retry post"]:
            target_post = None
            if message_obj and "reply_to_message" in message_obj:
                target_post = self._reconstruct_post_from_message(message_obj["reply_to_message"])
            if not target_post:
                target_post = db.get_latest_pending_post() or db.get_latest_post()

            if target_post:
                self._publish_post_now(target_post, chat_id)
            else:
                telegram_bot.send_message(
                    "ℹ️ No post draft found in database. Reply <b>'post now'</b> directly to a draft message in Telegram, or type <code>/draft</code> to create a new one!",
                    chat_id=chat_id
                )
            return

        if clean_text in ["/draft", "draft", "draft post", "create post", "generate post", "new post", "write a post"]:
            telegram_bot.send_message("🔍 Scouting trends and drafting your next Gen AI architecture post...", chat_id=chat_id)
            self.run_morning_content_pipeline()
            return

        if clean_text in ["/topics", "topics", "/vault", "vault", "knowledge vault"]:
            telegram_bot.send_message(knowledge_vault.get_vault_summary(), chat_id=chat_id)
            return

        if clean_text in ["/intimate", "intimate", "/weekly_prompt", "weekly prompt", "knowledge refresh"]:
            telegram_bot.send_weekly_intimation(chat_id=chat_id)
            return

        if any(clean_text.startswith(cmd) for cmd in ["/learn", "learn"]):
            rule_text = re.sub(r'^(?:/learn|learn)[:\s]*', '', text, flags=re.IGNORECASE).strip()
            if not rule_text:
                telegram_bot.send_message(
                    "🧠 <b>How to teach Buxbi:</b>\n\n"
                    "• <b>Teach New Tech:</b> <code>/learn Moonshine STT, vLLM chunked prefill, BitNet b1.58</code>\n"
                    "• <b>Teach a Writing Rule:</b> <code>/learn Always mention latency as a benchmark target.</code>\n"
                    "• <b>Send Documents:</b> Send any PDF or text file directly into this chat.\n\n"
                    "I will save technical insights into the Knowledge Vault and writing rules into persistent memory!",
                    chat_id=chat_id
                )
                return

            # Check if this is a negative/editorial rule or new technical concepts
            is_rule = any(w in rule_text.lower() for w in ["don't", "dont", "never", "avoid", "stop", "rule", "should not", "always use", "always avoid"])
            if not is_rule and ("," in rule_text or len(rule_text) > 40 or any(kw in rule_text.lower() for kw in ["architecture", "model", "paper", "framework", "vllm", "rag", "llm", "transformer", "latency"])):
                # Ingest as technical topic into Knowledge Vault
                telegram_bot.send_message("🔍 Analyzing technical concepts and ingesting into Knowledge Vault...", chat_id=chat_id)
                res = knowledge_vault.ingest_raw_text(rule_text, source_name="Telegram Note")
                if res.get("success"):
                    tech_lines = "\n".join([f"• <b>{t}</b>" for t in res.get("added_technologies", [])])
                    reply = (
                        f"🧠 <b>Learned and Stored in Knowledge Vault!</b>\n\n"
                        f"🔬 <b>Identified Technologies:</b>\n{tech_lines}\n\n"
                        f"💡 <b>Analysis:</b>\n{res.get('takeaways')}\n\n"
                        f"<i>I will prioritize these topics for our upcoming posts and animated GIFs!</i>"
                    )
                    inline_keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "🚀 Draft Post on This Now", "callback_data": "draft_new:0"},
                                {"text": "📚 View Knowledge Vault", "callback_data": "view_vault:0"}
                            ]
                        ]
                    }
                    telegram_bot.send_message(reply, reply_markup=inline_keyboard, chat_id=chat_id)
                else:
                    telegram_bot.send_message("⚠️ Could not process technical note.", chat_id=chat_id)
                return
            else:
                # Save as feedback writing rule
                saved_rule = feedback_memory.add_rule(rule_text)
                reply = (
                    "🧠 <b>Learned and Stored in Memory!</b>\n\n"
                    f"Rule: {saved_rule}\n\n"
                    "I will follow this rule for all upcoming post drafts and never repeat that mistake."
                )
                telegram_bot.send_message(reply, chat_id=chat_id)
                return

        if any(trigger in clean_text for trigger in [
            "/connections", "connections", "/network", "find leaders", "connection", "network", "scout",
            "relevant profile", "relevant profiles", "send profile", "send profiles", "leads"
        ]):
            telegram_bot.send_message("🤝 Sourcing 3 relevant Gen AI leaders and crafting personalized connection notes...", chat_id=chat_id)
            self.run_networking_pipeline(count=3, chat_id=chat_id)
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

        if clean_text in ["help", "/help", "menu", "/menu"]:
            help_text = (
                "👋 <b>Hey Madan! Here are your 1-click '/' options:</b>\n\n"
                "• <code>/draft</code> — Generate fresh Gen AI post + animated GIF\n"
                "• <code>/post</code> — Publish latest post to LinkedIn\n"
                "• <code>/connections</code> — Get 3 relevant Gen AI leaders + custom notes\n"
                "• <code>/repurpose &lt;url/text&gt;</code> — Turn an article or notes into a LinkedIn post\n"
                "• <code>/learn &lt;tech or rule&gt;</code> — Teach Buxbi a technology, document, or rule\n"
                "• <code>/topics</code> — View all topics currently in the Knowledge Vault\n"
                "• <code>/intimate</code> — Trigger the weekly knowledge refresh prompt\n"
                "• <code>/status</code> — View 24/7 cloud container health and active draft\n\n"
                "<i>You can click any command above or use the '/' menu button right beside your chat box!</i>"
            )
            telegram_bot.send_message(help_text, chat_id=chat_id)
            return

        if clean_text in ["status", "/status"]:
            pending = db.get_latest_pending_post() or db.get_latest_post()
            pending_info = f"Post #{pending['id']} [{pending['status']}] ('{pending['topic'][:35]}...')" if pending else "None"
            next_run_str = f"{config.SCHEDULE_TIME} ({config.TIMEZONE}) Daily"
            if getattr(self, "scheduler", None):
                job = self.scheduler.get_job("daily_linkedin_job")
                if job and job.next_run_time:
                    next_run_str = job.next_run_time.strftime("%A, %d %b %Y at %I:%M %p %Z")

            status_text = (
                "<b>🟢 BuxBi Status: ACTIVE &amp; 24/7 MONITORING</b>\n\n"
                f"• <b>Morning Schedule:</b> {next_run_str}\n"
                f"• <b>Latest Draft:</b> {pending_info}\n"
                f"• <b>Active Skills:</b> Post Writer, Humanizer, Content Planner, Authority Networker, Repurposer\n"
                f"• <b>Learned Rules:</b> {len(feedback_memory.rules)} feedback rules active in memory\n"
                f"• <b>Publishing Engine:</b> Publora Live Dispatch (60s UTC ISO-8601 + Auto-Verification)\n"
                f"• <b>Formatting Guard:</b> Zero Asterisks (*), Zero Arrows, Clean Bullets (•) and Numbers\n"
                f"• <b>Cloud Status:</b> Dual DB (SQLite/MySQL) + HTTP Healthcheck Server (port 10000)\n\n"
                "<i>Commands: /draft, /post, /connections, /repurpose, /learn, /status, /help</i>"
            )
            telegram_bot.send_message(status_text, chat_id=chat_id)
            return

        # 2. Conversational response via Groq
        system_prompt = """
You are Buxbi (also known as LinkBi), a sharp, helpful, and technically brilliant executive AI assistant for LinkedIn growth and Generative AI thought leadership.
You are chatting directly with your creator and user, Madan, via Telegram.

STRICT FORMATTING & TONE GUIDELINES:
1. Tone: Friendly, natural, concise, highly competent senior AI engineer/partner.
2. Address him naturally as Madan when appropriate.
3. Keep answers concise (1-3 short paragraphs), suited for mobile Telegram reading.
4. ABSOLUTELY NO ASTERISKS (* or **): Never use markdown bolding or asterisks anywhere in your reply. Telegram prints raw asterisks and it looks messy.
5. ABSOLUTELY NO ARROW SYMBOLS (↳, →, ⇒) or '#' markdown headers: Use ONLY plain sentences, standard numbers (1., 2., 3.), or simple bullet points (•).
6. If he asks about technical concepts, explain them clearly and naturally.
"""
        try:
            bot_reply = llm_client.generate(text, system_prompt=system_prompt, temperature=0.7)
            clean_reply = humanizer.clean_formatting(bot_reply)
            telegram_bot.send_message(clean_reply, chat_id=chat_id, parse_mode="")
        except Exception as e:
            logger.error(f"Error generating conversational reply: {e}")
            telegram_bot.send_message("I hear you, Madan! How can I assist you with your LinkedIn presence or posts right now?", chat_id=chat_id, parse_mode="")

orchestrator = AgentOrchestrator()
