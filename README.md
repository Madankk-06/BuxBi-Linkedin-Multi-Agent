# 🤖 Autonomous LinkedIn Gen AI Multi-Agent System

An autonomous, 24/7 LinkedIn management agent system specialized in **Generative AI**. It scouts breaking research, drafts viral technical posts using verified 2026 hook formulas, humanizes all text, identifies high-authority AI leaders, and sends interactive approval cards directly to your **Telegram** before anything is posted.

---

## 🌟 Key Features

1. **Pure Standalone Python Service:** Runs independently without needing Claude Code, Codex, or complex IDE setups.
2. **Runs While Laptop is Closed (24/7 Cloud Support):** Deployable to free cloud platforms (Render, Railway, Fly.io) with 1 click.
3. **Gen AI Domain Radar:** Automatically monitors ArXiv papers, Hugging Face releases, and frontier breakthroughs.
4. **2026 Verified Hook Formulas:** Uses number-first openers, false-binary dissolves, and architecture comparisons in the 900–1,300 char sweet spot.
5. **4-Pass Humanizer:** Strips AI buzzwords (*delve, tapestry, pivotal, foster*), eliminates reveal bridges, and normalizes sentence rhythm.
6. **Safe High-Authority Connection Assist:** Sourced leaders (Founders, Lab Scientists, VCs) + bespoke notes (<300 chars) delivered to your phone for manual 1-click sending. **Zero risk of LinkedIn account bans.**
7. **Interactive Telegram Approval:** Tap `[✅ Approve & Post Now]`, `[📅 Schedule]`, or `[🔄 Regenerate]` straight from your phone.

---

## 📁 Project Architecture

```
Linkedin_Agent/
├── agents/
│   ├── trend_scout.py          # Monitors ArXiv & AI research drops
│   ├── post_architect.py       # Drafts posts using 2026 hook formulas
│   ├── humanizer.py            # 4-pass anti-AI tell sanitizer
│   └── authority_networker.py  # High-authority leader scout + 300-char notes
├── core/
│   ├── config.py               # Central environment configuration
│   └── database.py             # SQLite persistence for posts & connections
├── lib/
│   ├── arxiv_client.py         # ArXiv API scientific scraper
│   ├── llm_client.py           # Multi-provider LLM caller (Gemini/OpenAI/Anthropic)
│   ├── telegram_bot.py         # Interactive Telegram Bot integration
│   └── publora_client.py       # LinkedIn posting API (optional)
├── scripts/
│   └── test_pipeline.py        # Dry-run test harness
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
├── main.py                     # 24/7 background scheduler & bot listener
├── Dockerfile                  # Container definition for cloud hosting
└── render.yaml                 # 1-click Render.com deployment manifest
```

---

## ⚡ Quick Start Guide (5 Minutes)

### Step 1: Create Your Telegram Bot (Takes 60 seconds)
1. Open Telegram on your phone or desktop and search for **`@BotFather`**.
2. Send `/newbot` and follow the prompts to name your bot.
3. Copy the **HTTP API Token** provided (e.g. `789123456:AAH...`).
4. Next, search for **`@userinfobot`** on Telegram and click `Start`. It will reply with your **Id** (a number like `123456789`).
5. Open your newly created bot in Telegram and tap **Start** to initialize communication.

### Step 2: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` and fill in your keys:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_id_from_userinfobot

# Recommended Free LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key

# Optional (for automated publishing)
PUBLORA_API_KEY=
LINKEDIN_PLATFORM_ID=
```

### Step 3: Install & Run Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run the test script to verify everything works
python scripts/test_pipeline.py --mode all

# Start the 24/7 background scheduler & Telegram listener
python main.py
```

---

## ☁️ Running 24/7 While Laptop Is Closed (100% Free on Render.com)

1. Push this folder to a private **GitHub repository**.
2. Go to [Render.com](https://render.com) (free account) and click **New + → Background Worker**.
3. Select your repository. Render will automatically detect `render.yaml` or `Dockerfile`.
4. Add your `.env` variables under **Environment Variables**:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
5. Click **Create Background Worker**.
6. **Done!** The agent will run 24/7 in the cloud, scouting trends and pinging your Telegram every morning—even if your computer is completely shut down.

---

## 📱 Telegram Bot Commands

You can message your bot directly at any time:
- `/draft_post` — Forces an immediate Gen AI post draft and sends the approval card.
- `/find_leaders` — Instantly delivers high-authority connection candidates + notes.
- `/status` — Displays agent health, database statistics, and scheduled times.
- `/help` — Lists all available commands.
