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
        self._publishing_in_progress: set[int] = set()

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

    def _resolve_media_for_publishing(self, post: dict) -> Optional[str]:
        """Resolve the final media path/URL to publish with LinkedIn.
        - Preserves user-uploaded photos (JPG, PNG, WebP) with 100% fidelity.
        - Ensures animations/GIFs are sent as pure CompuServe GIF89a images (never MP4 videos).
        - Falls back to the master generated architectural GIF if no user media is attached.
        """
        post_id = post["id"]
        raw_media = post.get("image_url")
        master_gif = f"data/generated_gifs/post_{post_id}_arch.gif"

        # If no media attached, use the generated master architectural GIF if it exists
        if not raw_media:
            return master_gif if os.path.exists(master_gif) else None

        media_str = str(raw_media).strip()

        # If remote URL
        if media_str.startswith("http://") or media_str.startswith("https://"):
            if media_str.lower().endswith(".mp4") and os.path.exists(master_gif):
                return master_gif
            return media_str

        # If local file
        local_path = media_str
        if not os.path.exists(local_path):
            if os.path.exists(master_gif):
                return master_gif
            return local_path

        try:
            with open(local_path, "rb") as f:
                hdr = f.read(16)

            # 1. Custom user-uploaded photo (JPEG, PNG, WebP) -> PRESERVE!
            if hdr.startswith(b"\xff\xd8\xff") or hdr.startswith(b"\x89PNG") or hdr.startswith(b"RIFF"):
                logger.info(f"Preserving custom user-uploaded photo for publishing: {local_path}")
                return local_path

            # 2. Genuine GIF (GIF87a / GIF89a) -> PRESERVE!
            if hdr.startswith(b"GIF87a") or hdr.startswith(b"GIF89a"):
                return local_path

            # 3. MP4 / Video container -> Swap to master GIF or convert
            if b"ftyp" in hdr or hdr.startswith(b"\x00\x00\x00") or local_path.lower().endswith(".mp4"):
                if os.path.exists(master_gif):
                    logger.info(f"Swapping MP4 file {local_path} with pristine Master GIF {master_gif}")
                    return master_gif

                from lib.gif_engine import find_ffmpeg
                ffmpeg_exe = find_ffmpeg()
                if ffmpeg_exe:
                    conv = str(Path(local_path).with_suffix(".pure.gif"))
                    cmd = [
                        ffmpeg_exe, "-y",
                        "-i", local_path,
                        "-vf", "fps=10,split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
                        conv
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)
                    return conv
        except Exception as e:
            logger.warning(f"Error inspecting media bytes for {local_path}: {e}")

        # Check standard image extensions
        ext = os.path.splitext(local_path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            return local_path

        if os.path.exists(master_gif):
            return master_gif
        return local_path

    def _publish_post_now(self, post: dict, chat_id: str) -> bool:
        """Publish a post immediately via Publora (schedules 60s out in UTC ISO-8601 and verifies live status).
        Includes strict concurrency lock and database idempotency guards to prevent duplicate LinkedIn posts.
        """
        post_id = post["id"]

        # 1. Concurrency guard: prevent multiple parallel executions for the exact same post
        if post_id in self._publishing_in_progress:
            logger.warning(f"Publishing already in progress for post #{post_id}. Ignoring duplicate trigger.")
            telegram_bot.send_message(f"⏳ Post #{post_id} is already being published to LinkedIn. Please wait...", chat_id=chat_id)
            return True

        # 2. Database idempotency guard: prevent duplicate live dispatches if already queued
        fresh_post = db.get_post(post_id) or post
        if fresh_post.get("status") in ("approved", "published") and fresh_post.get("post_urn"):
            publora_id = fresh_post.get("post_urn")
            logger.warning(f"Post #{post_id} already has active Publora ID '{publora_id}'. Preventing duplicate LinkedIn post.")
            telegram_bot.send_message(
                f"ℹ️ <b>Post #{post_id} is already queued/published!</b>\n\n"
                f"🆔 <b>Publora ID:</b> <code>{publora_id}</code>\n"
                f"To protect your LinkedIn profile and Publora queue, duplicate submission was prevented.\n"
                f"🔗 <a href='https://www.linkedin.com/in/madankk04122004/recent-activity/all/'>Open LinkedIn Activity</a>",
                chat_id=chat_id
            )
            return True

        self._publishing_in_progress.add(post_id)
        try:
            db.update_post_status(post_id, "approved")

            if publora_client.is_configured:
                media_to_publish = self._resolve_media_for_publishing(fresh_post)
                logger.info(f"Selected media for LinkedIn publishing: {media_to_publish}")

                res = publora_client.publish_or_schedule_post(
                    fresh_post["draft_text"],
                    scheduled_time=None,
                    image_path=media_to_publish
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
                    f"<pre>{fresh_post['draft_text']}</pre>"
                )
                telegram_bot.send_message(msg, chat_id=chat_id)
                return True
        finally:
            self._publishing_in_progress.discard(post_id)

    def handle_callback_action(self, callback_data: str, chat_id: str, message_id: int, message_obj: Optional[dict] = None):
        """Handle button clicks from Telegram."""
        parts = callback_data.split(":")
        action = parts[0]
        if len(parts) >= 4:
            sub_param = parts[1]
            sub_param2 = parts[2]
            post_id_str = parts[3]
        elif len(parts) == 3:
            sub_param = parts[1]
            sub_param2 = None
            post_id_str = parts[2]
        elif len(parts) == 2:
            sub_param = None
            sub_param2 = None
            post_id_str = parts[1]
        else:
            sub_param = None
            sub_param2 = None
            post_id_str = "0"

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
            telegram_bot.send_gif_customization_menu(post_id=post_id, current_theme="5", current_size="poster", chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "gif_sel_t":
            sel_theme = sub_param or "5"
            sel_size = sub_param2 or "poster"
            telegram_bot.edit_gif_customization_menu(chat_id, message_id, post_id, selected_theme=sel_theme, selected_size=sel_size)
            return

        elif action == "gif_sel_s":
            sel_theme = sub_param or "5"
            sel_size = sub_param2 or "poster"
            telegram_bot.edit_gif_customization_menu(chat_id, message_id, post_id, selected_theme=sel_theme, selected_size=sel_size)
            return

        elif action == "gif_go":
            theme_id = sub_param or "5"
            size_preset = sub_param2 or "poster"
            theme_names = {
                "5": "Champagne & Bronze",
                "6": "Graphite & Blue",
                "4": "Royal Amethyst"
            }
            size_names = {
                "poster": "Poster (1400x800)",
                "landscape": "Landscape (1200x630)",
                "portrait": "Portrait (1080x1350)",
                "square": "Square (1080x1080)"
            }
            t_display = theme_names.get(theme_id, f"Theme {theme_id}")
            s_display = size_names.get(size_preset, size_preset.title())

            telegram_bot.send_message(
                f"⚙️ <b>Re-creating animated GIF...</b>\n\n"
                f"🎨 <b>Theme:</b> {t_display}\n"
                f"📐 <b>Resolution:</b> {s_display}\n\n"
                f"<i>Synthesizing both selections into a master-quality GIF...</i>",
                chat_id=chat_id
            )

            spec_file = Path(f"data/generated_gifs/post_{post_id}_spec.txt")
            if spec_file.exists():
                with open(spec_file, "r", encoding="utf-8") as f:
                    spec_text = f.read()
            else:
                spec_text = gif_engine.design_architecture_spec(post["topic"], post["draft_text"])

            ts = int(time.time())
            new_gif_path = f"data/generated_gifs/post_{post_id}_t{theme_id}_{size_preset}_{ts}.gif"
            gif_engine.render_gif(
                spec_text,
                theme=theme_id,
                size=size_preset,
                output_path=new_gif_path,
                fps=10,
                duration=4.0
            )

            # 1. Permanently store new pure GIF binary into database blob
            try:
                with open(new_gif_path, "rb") as f:
                    raw_bytes = f.read()
                db.save_post_media_blob(post_id, raw_bytes, os.path.basename(new_gif_path), "image/gif")
            except Exception as e:
                logger.warning(f"Could not save re-created GIF to DB: {e}")

            # 2. Upload to Catbox CDN to get fresh 1-click download link
            public_url = publora_client.upload_local_media(new_gif_path, post_id=post_id)
            stored_ref = public_url or new_gif_path
            db.update_post_image(post_id, stored_ref)
            post["image_url"] = stored_ref

            # 3. Clean up the customization menu
            telegram_bot.edit_message_reply_markup(chat_id, message_id)

            # 4. Send updated Post Approval Card with the new GIF download link!
            telegram_bot.send_post_approval_card(
                post_id=post_id,
                topic=post["topic"],
                hook_formula=post.get("hook_formula", ""),
                draft_text=post["draft_text"],
                image_url=new_gif_path,
                chat_id=chat_id
            )
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
        if action == "noop":
            return

        elif action == "upload_image":
            self.pending_image_upload_post_id = post_id
            try:
                Path("data").mkdir(parents=True, exist_ok=True)
                Path("data/pending_upload.txt").write_text(str(post_id))
            except Exception:
                pass
            msg = (
                f"📸 <b>Awaiting Your Custom Image for Post #{post_id}!</b>\n\n"
                f"Please send or drop your photo/graphic (JPG, PNG, or GIF) right here in the chat.\n"
                f"I will attach it to your post content and ask for your final confirmation before posting!"
            )
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action in ("confirm_post", "approve_now"):
            # 1. Immediately disable buttons in UI to prevent double/triple clicks
            telegram_bot.edit_message_reply_markup(
                chat_id, message_id,
                reply_markup={"inline_keyboard": [[{"text": "⏳ Publishing to LinkedIn in progress...", "callback_data": "noop"}]]}
            )
            self._publish_post_now(post, chat_id)
            return

        elif action == "schedule_slot":
            # 1. Immediately disable buttons in UI to prevent double/triple clicks
            telegram_bot.edit_message_reply_markup(
                chat_id, message_id,
                reply_markup={"inline_keyboard": [[{"text": "⏳ Scheduling on Publora in progress...", "callback_data": "noop"}]]}
            )

            fresh_post = db.get_post(post_id) or post
            if fresh_post.get("status") == "scheduled" and fresh_post.get("post_urn"):
                telegram_bot.send_message(
                    f"ℹ️ <b>Post #{post_id} is already scheduled on Publora!</b> (ID: <code>{fresh_post.get('post_urn')}</code>)",
                    chat_id=chat_id
                )
                return

            if publora_client.is_configured:
                media_to_publish = self._resolve_media_for_publishing(fresh_post)
                res = publora_client.publish_or_schedule_post(
                    fresh_post["draft_text"],
                    scheduled_time="08:30",
                    image_path=media_to_publish
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
            return

        elif action == "regen_post":
            telegram_bot.send_message(f"🔄 Regenerating angle for Post #{post_id}...", chat_id=chat_id)
            self.run_morning_content_pipeline()

        elif action == "discard_post":
            db.update_post_status(post_id, "discarded")
            telegram_bot.send_message(f"🗑️ Post #{post_id} has been discarded.", chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)


    def handle_user_image(self, file_id: str, chat_id: str, media_kind: str = "photo",
                          file_name: Optional[str] = None, mime_type: Optional[str] = None,
                          reply_msg: Optional[dict] = None):
        """Receive media (photo / GIF / MP4) from the user, attach it to the right post draft,
        and send back the combined post (media + full post content) for final confirmation."""
        target_post = None

        # 1. If the user replied to a specific draft card, attach to exactly that post
        if reply_msg:
            reply_text = reply_msg.get("text") or reply_msg.get("caption") or ""
            m = re.search(r"Post #(\d+)", reply_text)
            if m:
                target_post = db.get_post(int(m.group(1)))
            if not target_post:
                target_post = self._reconstruct_post_from_message(reply_msg)

        # 2. Explicit "Upload Photo" button target
        if not target_post and self.pending_image_upload_post_id:
            target_post = db.get_post(self.pending_image_upload_post_id)

        # 2b. Check persistent file if server restarted
        if not target_post:
            pending_file = Path("data/pending_upload.txt")
            if pending_file.exists():
                try:
                    p_id = int(pending_file.read_text().strip())
                    target_post = db.get_post(p_id)
                except Exception:
                    pass

        # 3. Latest pending draft
        if not target_post:
            target_post = db.get_latest_pending_post() or db.get_latest_post()

        if not target_post:
            telegram_bot.send_message(
                "📸 I received your media, but I could not find the post draft it belongs to "
                "(the server may have restarted).\n\n"
                "👉 Long-press the post draft card, tap <b>Reply</b>, and send the photo again as the reply. "
                "Or type <b>draft post</b> to create a new draft.",
                chat_id=chat_id
            )
            return

        post_id = target_post["id"]
        telegram_bot.send_message(
            f"📥 Got your media! Attaching it to <b>Post #{post_id}</b> and preparing the final combined post...",
            chat_id=chat_id
        )

        mime = (mime_type or "").lower()
        name_ext = os.path.splitext(file_name or "")[1].lower()
        ext = name_ext or (".png" if mime == "image/png" else (".gif" if mime == "image/gif" else ".jpg"))

        Path("data/user_uploads").mkdir(parents=True, exist_ok=True)
        dest_path = f"data/user_uploads/post_{post_id}_{int(time.time())}{ext}"
        downloaded = telegram_bot.download_file(file_id, dest_path)
        if not downloaded:
            telegram_bot.send_message("⚠️ Could not download the media. Please try sending it again.", chat_id=chat_id)
            return

        # Inspect real binary magic bytes
        hdr = b""
        try:
            with open(downloaded, "rb") as f_check:
                hdr = f_check.read(16)
        except Exception:
            pass

        is_jpeg = hdr.startswith(b"\xff\xd8\xff")
        is_png = hdr.startswith(b"\x89PNG")
        is_webp = hdr.startswith(b"RIFF") and b"WEBP" in hdr
        is_pure_gif = hdr.startswith(b"GIF87a") or hdr.startswith(b"GIF89a")
        is_mp4 = (b"ftyp" in hdr) or hdr.startswith(b"\x00\x00\x00") or media_kind in ("animation", "video")

        master_gif = f"data/generated_gifs/post_{post_id}_arch.gif"

        # CASE A: User uploaded a Custom Photo (JPG / PNG / WebP)
        if is_jpeg or is_png or is_webp or media_kind == "photo" or (ext in (".jpg", ".jpeg", ".png", ".webp") and not is_pure_gif and not is_mp4):
            real_ext = ".png" if is_png else (".webp" if is_webp else ".jpg")
            real_mime = "image/png" if is_png else ("image/webp" if is_webp else "image/jpeg")
            final_media_path = str(Path(downloaded).with_suffix(real_ext))
            if downloaded != final_media_path:
                try:
                    os.rename(downloaded, final_media_path)
                except Exception:
                    final_media_path = downloaded

            logger.info(f"User uploaded valid custom photo for Post #{post_id}: {final_media_path} ({real_mime})")

            # 1. Save photo blob to DB
            try:
                with open(final_media_path, "rb") as f:
                    media_bytes = f.read()
                db.save_post_media_blob(post_id, media_bytes, os.path.basename(final_media_path), real_mime)
            except Exception as e:
                logger.warning(f"Could not save user photo blob to DB: {e}")

            # 2. Upload to public CDN
            public_url = publora_client.upload_local_media(final_media_path, post_id=post_id)
            stored_image_ref = public_url or final_media_path
            db.update_post_image(post_id, stored_image_ref)

            # 3. Clean up pending state
            self.pending_image_upload_post_id = None
            try:
                Path("data/pending_upload.txt").unlink(missing_ok=True)
            except Exception:
                pass

            # 4. Send final confirmation card showing the actual photo preview!
            telegram_bot.send_final_confirmation_card(
                post_id=post_id,
                topic=target_post["topic"],
                draft_text=target_post["draft_text"],
                image_url=final_media_path,
                chat_id=chat_id,
                public_media_url=public_url,
                telegram_file_id=file_id,
                media_kind="photo"
            )
            return

        # CASE B: Animation / GIF / Video
        gif_target_path = downloaded
        if is_mp4 or (not is_pure_gif and ext == ".gif"):
            from lib.gif_engine import find_ffmpeg
            ffmpeg_exe = find_ffmpeg()
            converted_gif = str(Path(downloaded).with_name(f"post_{post_id}_{int(time.time())}_pure.gif"))
            if ffmpeg_exe:
                try:
                    logger.info(f"Converting Telegram MP4/video {downloaded} to high-fidelity GIF {converted_gif}...")
                    cmd_conv = [
                        ffmpeg_exe, "-y",
                        "-i", downloaded,
                        "-vf", "fps=10,split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3",
                        converted_gif
                    ]
                    subprocess.run(cmd_conv, capture_output=True, check=True)
                    gif_target_path = converted_gif
                    logger.info(f"Successfully converted MP4 to pure GIF: {gif_target_path}")
                except Exception as e_conv:
                    logger.warning(f"Notice: MP4 to GIF conversion failed: {e_conv}")
                    if os.path.exists(master_gif):
                        gif_target_path = master_gif

        # If user sent back an unedited/downscaled version of the generated post GIF (Telegram downscales animations to 320px)
        if is_pure_gif and os.path.exists(master_gif) and os.path.exists(gif_target_path):
            try:
                if os.path.getsize(gif_target_path) < 150_000 and os.path.getsize(master_gif) > 300_000:
                    logger.info(f"Detected low-res Telegram delivery ({os.path.getsize(gif_target_path)} bytes). Retaining Master 2800x1600 GIF ({os.path.getsize(master_gif)} bytes).")
                    gif_target_path = master_gif
            except Exception:
                pass

        # Save pure GIF binary into MySQL/SQLite DB
        try:
            with open(gif_target_path, "rb") as f:
                media_bytes = f.read()
            db.save_post_media_blob(post_id, media_bytes, os.path.basename(gif_target_path), "image/gif")
        except Exception as e:
            logger.warning(f"Could not save user upload blob to DB: {e}")

        # Upload pure GIF to public CDN
        public_url = publora_client.upload_local_media(gif_target_path, post_id=post_id)
        stored_image_ref = public_url or gif_target_path
        db.update_post_image(post_id, stored_image_ref)

        self.pending_image_upload_post_id = None
        try:
            Path("data/pending_upload.txt").unlink(missing_ok=True)
        except Exception:
            pass

        telegram_bot.send_final_confirmation_card(
            post_id=post_id,
            topic=target_post["topic"],
            draft_text=target_post["draft_text"],
            image_url=gif_target_path,
            chat_id=chat_id,
            public_media_url=public_url,
            telegram_file_id=file_id,
            media_kind="document"
        )

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
        if result.get("success") and result.get("added_count", 0) > 0:
            tech_names = result.get("added_technologies", [])
            tech_lines = "\n".join([f"• <b>{t}</b>" for t in tech_names[:8]])
            if len(tech_names) > 8:
                tech_lines += f"\n<i>...and {len(tech_names) - 8} more topics queued!</i>"
            first_topic = tech_names[0] if tech_names else "Learned Topics"
            reply = (
                f"🧠 <b>Document Successfully Ingested into Knowledge Vault!</b>\n\n"
                f"📄 <b>File:</b> {file_name}\n"
                f"🔬 <b>Extracted Technologies ({result.get('added_count')}):</b>\n{tech_lines}\n\n"
                f"💡 <b>Architectural Takeaways:</b>\n{result.get('takeaways')}\n\n"
                f"<i>Next post target: <b>{first_topic}</b>. These concepts are now locked into persistent memory for upcoming daily posts and animated GIFs!</i>"
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
            err = result.get("error") or "No readable technical content could be extracted from this document."
            telegram_bot.send_message(f"⚠️ Ingestion error: {err}\n\nPlease provide a valid .docx, .pdf, or .txt file, or paste your topics directly in chat!", chat_id=chat_id)

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

        if clean_text in [
            "all", "learn all", "add all", "save all", "learn them", "save these",
            "proceed with 1st option", "proceed with all", "proceed", "1st option", "first option"
        ]:
            priority = knowledge_vault.get_priority_topic()
            if priority and priority.get("status") == "new":
                topic_name = priority.get("name")
                telegram_bot.send_message(
                    f"🚀 <b>Proceeding with priority topic:</b> {topic_name}\n"
                    "Drafting post and rendering animated architectural GIF...",
                    chat_id=chat_id
                )
            else:
                telegram_bot.send_message(
                    "🚀 Drafting next Gen AI thought leadership post...",
                    chat_id=chat_id
                )
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
                    "• <b>Teach New Tech:</b> <code>/learn AI Guardrails, Synthetic Data, MCP vs Function Calling</code>\n"
                    "• <b>Paste Topic Lists:</b> Paste multiple topics directly as text into this chat.\n"
                    "• <b>Send Documents:</b> Send any Word (.docx), PDF, or text file directly.\n"
                    "• <b>Teach a Writing Rule:</b> <code>/learn Never use buzzwords like 'game-changer'.</code>\n\n"
                    "I will save technical topics into the Knowledge Vault for upcoming posts and writing rules into persistent memory!",
                    chat_id=chat_id
                )
                return

            # Check if this is a negative/editorial rule or new technical concepts
            is_rule = any(w in rule_text.lower() for w in ["don't", "dont", "never", "avoid", "stop", "rule", "should not", "always use", "always avoid", "do not"])
            if is_rule:
                # Save as feedback writing rule
                saved_rule = feedback_memory.add_rule(rule_text)
                reply = (
                    "🧠 <b>Learned and Stored in Memory!</b>\n\n"
                    f"Rule: {saved_rule}\n\n"
                    "I will follow this rule for all upcoming post drafts and never repeat that mistake."
                )
                telegram_bot.send_message(reply, chat_id=chat_id)
                return
            else:
                # Ingest as technical topic into Knowledge Vault
                telegram_bot.send_message("🔍 Analyzing technical topic(s) and ingesting into Knowledge Vault...", chat_id=chat_id)
                res = knowledge_vault.ingest_raw_text(rule_text, source_name="Telegram /learn")
                if res.get("success") and res.get("added_count", 0) > 0:
                    tech_names = res.get("added_technologies", [])
                    tech_lines = "\n".join([f"• <b>{t}</b>" for t in tech_names[:8]])
                    if len(tech_names) > 8:
                        tech_lines += f"\n<i>...and {len(tech_names) - 8} more topics queued!</i>"
                    first_topic = tech_names[0] if tech_names else "Learned Topics"
                    reply = (
                        f"🧠 <b>Learned and Stored in Knowledge Vault!</b>\n\n"
                        f"🔬 <b>Identified Technologies ({res.get('added_count')}):</b>\n{tech_lines}\n\n"
                        f"💡 <b>Analysis:</b>\n{res.get('takeaways')}\n\n"
                        f"<i>Next post target: <b>{first_topic}</b>. These concepts are queued for your upcoming LinkedIn posts and animated GIFs!</i>"
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

        # Check if user pasted a list of topics (2+ discrete lines of technical concepts)
        if not clean_text.startswith("/"):
            from core.knowledge_vault import extract_topic_items_from_text
            pasted_topics = extract_topic_items_from_text(text)
            if len(pasted_topics) >= 2:
                telegram_bot.send_message(
                    f"🧠 <b>Detected {len(pasted_topics)} technical topics!</b>\n"
                    "Analyzing each topic architecture and ingesting into Knowledge Vault...",
                    chat_id=chat_id
                )
                res = knowledge_vault.ingest_raw_text(text, source_name="Pasted Topics")
                if res.get("success") and res.get("added_count", 0) > 0:
                    tech_names = res.get("added_technologies", [])
                    tech_lines = "\n".join([f"• <b>{t}</b>" for t in tech_names[:8]])
                    if len(tech_names) > 8:
                        tech_lines += f"\n<i>...and {len(tech_names) - 8} more topics queued!</i>"
                    first_topic = tech_names[0] if tech_names else "Learned Topics"
                    reply = (
                        f"🧠 <b>Successfully Learned {res.get('added_count')} Topics!</b>\n\n"
                        f"🔬 <b>Queued for Upcoming Posts:</b>\n{tech_lines}\n\n"
                        f"💡 <b>Architectural Summary:</b>\n{res.get('takeaways')}\n\n"
                        f"<i>Next scheduled post will be on: <b>{first_topic}</b>!</i>"
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
