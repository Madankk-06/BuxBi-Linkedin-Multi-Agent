import logging
from typing import Optional
from agents.trend_scout import trend_scout
from agents.domain_director import domain_director
from agents.post_architect import post_architect
from agents.humanizer import humanizer
from agents.authority_networker import authority_networker
from agents.image_architect import image_architect
from lib.telegram_bot import telegram_bot
from lib.publora_client import publora_client
from core.database import db

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self):
        self.pending_image_upload_post_id: Optional[int] = None

    def run_morning_content_pipeline(self) -> int:
        """Autonomous pipeline: Select diverse Gen AI domain -> Draft practitioner post -> Humanize -> Render architecture card -> Telegram."""
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
        
        # 6. Send Interactive Approval Card + Visual Card to Telegram
        telegram_bot.send_post_approval_card(
            post_id=post_id,
            topic=topic_title,
            hook_formula=formula,
            draft_text=final_draft,
            image_url=image_path
        )
        logger.info(f"Sent approval card for post #{post_id} to Telegram.")
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

    def handle_callback_action(self, callback_data: str, chat_id: str, message_id: int):
        """Handle button clicks from Telegram."""
        action, post_id_str = callback_data.split(":")
        post_id = int(post_id_str)
        post = db.get_post(post_id)

        if not post:
            telegram_bot.send_message("❌ Error: Post draft not found in database.", chat_id=chat_id)
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
                db.update_post_image(post_id, img_path)
                telegram_bot.send_final_confirmation_card(
                    post_id=post_id,
                    topic=post["topic"],
                    draft_text=post["draft_text"],
                    image_url=img_path,
                    theme_name=theme_name,
                    chat_id=chat_id
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
                f"I will draft it with the post content and ask for your final confirmation before posting!"
            )
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "confirm_post":
            db.update_post_status(post_id, "approved")
            if publora_client.is_configured:
                res = publora_client.publish_or_schedule_post(post["draft_text"], image_path=post.get("image_url"))
                if res.get("success"):
                    msg = f"🎉 <b>Post #{post_id} Confirmed & Published Live to LinkedIn!</b>\n🔗 <a href='https://www.linkedin.com/in/madankk04122004/'>View on your LinkedIn Profile</a>"
                else:
                    msg = f"⚠️ Confirmed, but Publora returned: {res.get('error')}"
            else:
                msg = (
                    f"🎉 <b>Post #{post_id} Confirmed & Ready for LinkedIn!</b>\n\n"
                    f"<b>Topic:</b> {post['topic']}\n"
                    f"<b>Attached Image:</b> {post.get('image_url')}\n\n"
                    f"<i>Copy post text below:</i>\n\n"
                    f"<pre>{post['draft_text']}</pre>"
                )
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)
            return

        elif action == "approve_now":
            db.update_post_status(post_id, "approved")
            # If Publora configured, publish live
            if publora_client.is_configured:
                res = publora_client.publish_or_schedule_post(post["draft_text"], image_path=post.get("image_url"))
                if res.get("success"):
                    msg = f"🚀 <b>Post #{post_id} Approved & Published Live to LinkedIn!</b>\n🔗 <a href='https://www.linkedin.com/in/madankk04122004/'>View on your LinkedIn Profile</a>"
                else:
                    msg = f"⚠️ Approved, but Publora returned: {res.get('error')}"
            else:
                msg = (
                    f"✅ <b>Post #{post_id} Approved!</b>\n\n"
                    f"<i>(Publora API not configured, so copy and paste directly to LinkedIn):</i>\n\n"
                    f"<pre>{post['draft_text']}</pre>"
                )
            telegram_bot.send_message(msg, chat_id=chat_id)
            telegram_bot.edit_message_reply_markup(chat_id, message_id)

        elif action == "schedule_slot":
            db.update_post_status(post_id, "scheduled", scheduled_time="08:30")
            msg = f"📅 <b>Post #{post_id} Scheduled for Tomorrow at 08:30 AM!</b>"
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
        """Receive a custom image sent by the user in Telegram, attach it, and ask for confirmation."""
        import time
        target_post = None
        if self.pending_image_upload_post_id:
            target_post = db.get_post(self.pending_image_upload_post_id)
            
        if not target_post:
            target_post = db.get_latest_pending_post()
            
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
            db.update_post_image(post_id, downloaded)
            self.pending_image_upload_post_id = None
            # Show preview with the image and request confirmation
            telegram_bot.send_final_confirmation_card(
                post_id=post_id,
                topic=target_post["topic"],
                draft_text=target_post["draft_text"],
                image_url=downloaded,
                chat_id=chat_id
            )
        else:
            telegram_bot.send_message("⚠️ Could not download the image. Please try sending it again.", chat_id=chat_id)

    def handle_conversational_text(self, text: str, chat_id: str):
        """Handle conversational commands, questions, and instructions from the user in Telegram."""
        from lib.llm_client import llm_client
        clean_text = text.strip().lower()

        # 1. Quick command intents
        if clean_text in ["post now", "publish", "approve", "approve now"]:
            pending_post = db.get_latest_pending_post()
            if pending_post:
                post_id = pending_post["id"]
                db.update_post_status(post_id, "approved")
                if publora_client.is_configured:
                    res = publora_client.publish_or_schedule_post(pending_post["draft_text"], image_path=pending_post.get("image_url"))
                    if res.get("success"):
                        reply = f"🚀 <b>Post #{post_id} Approved & Published Live to LinkedIn!</b>\n🔗 <a href='https://www.linkedin.com/in/madankk04122004/'>View on your LinkedIn Profile</a>"
                    else:
                        reply = f"⚠️ Approved, but Publora returned: {res.get('error')}"
                else:
                    reply = (
                        f"✅ <b>Post #{post_id} Approved!</b>\n\n"
                        f"<b>Topic:</b> {pending_post['topic']}\n"
                        f"<b>Attached Image:</b> {pending_post.get('image_url') or 'Default Architecture Graphic'}\n\n"
                        f"<i>Ready for LinkedIn! Copy post text below:</i>\n\n"
                        f"<pre>{pending_post['draft_text']}</pre>"
                    )
                telegram_bot.send_message(reply, chat_id=chat_id)
                # If image exists, resend it to the chat for quick saving
                if pending_post.get("image_url"):
                    telegram_bot.send_photo(pending_post["image_url"], caption=f"🖼 Image for Post #{post_id}", chat_id=chat_id)
            else:
                telegram_bot.send_message("ℹ️ No pending post draft found to approve. Type <b>'draft post'</b> to create one!", chat_id=chat_id)
            return

        if any(trigger in clean_text for trigger in ["draft post", "create post", "generate post", "new post", "write a post"]):
            telegram_bot.send_message("🔍 Scouting trends & drafting your next Gen AI architecture post...", chat_id=chat_id)
            self.run_morning_content_pipeline()
            return

        if any(trigger in clean_text for trigger in ["find leaders", "connections", "network", "scout leaders"]):
            telegram_bot.send_message("🤝 Sourcing top Gen AI authorities & crafting bespoke connection notes...", chat_id=chat_id)
            self.run_networking_pipeline(count=3)
            return

        if clean_text in ["status", "/status"]:
            pending = db.get_latest_pending_post()
            pending_info = f"Post #{pending['id']} ('{pending['topic'][:35]}...')" if pending else "None"
            status_text = (
                "<b>🟢 BuxBi Status: ACTIVE & LISTENING</b>\n\n"
                f"• <b>Pending Draft:</b> {pending_info}\n"
                f"• <b>Workflow:</b> Custom image upload + conversational commands enabled\n"
                f"• <b>LLM:</b> Groq (qwen/qwen3.8-27b)\n\n"
                "<i>You can talk to me, ask me questions about AI architectures, ask me to draft posts, or send me an image to attach!</i>"
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
