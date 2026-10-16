import logging
from typing import Optional
from lib.arxiv_client import arxiv_client
from lib.llm_client import llm_client
from core.database import db

logger = logging.getLogger(__name__)

class TrendScoutAgent:
    def scout_latest_trends(self) -> list[dict]:
        """Scout scientific and industry sources for breaking Gen AI topics."""
        papers = arxiv_client.fetch_latest_genai_papers(max_results=5)
        
        # Save to database
        for p in papers:
            db.save_trend(p["source"], p["title"], p["url"], p["summary"])
            
        return papers

    def select_best_topic(self, trends: list[dict]) -> dict:
        """Analyze candidates and select the single highest-impact topic for LinkedIn engagement."""
        candidates_summary = "\n\n".join([
            f"Candidate {i+1}:\nTitle: {t['title']}\nSummary: {t['summary']}\nURL: {t['url']}"
            for i, t in enumerate(trends)
        ])

        prompt = f"""
You are the Gen AI Trend Scout Agent for an executive-tier LinkedIn presence.
Evaluate these recent breakthrough candidates:

{candidates_summary}

Select the SINGLE most commercially and technically impactful topic for a LinkedIn audience (Founders, Staff Engineers, AI VCs, Heads of AI).
Criteria:
- Must spark debate, solve a real architecture headache, or reveal a non-obvious shift (e.g. test-time compute, reasoning agents, cost per token, context caching).
- Avoid generic consumer AI hype. Focus on real architecture / systems.

Output format (strictly valid JSON with no markdown wrapping):
{{
  "selected_title": "...",
  "core_breakthrough": "...",
  "why_it_matters": "...",
  "contrarian_take": "...",
  "source_url": "..."
}}
"""
        response = llm_client.generate(prompt, temperature=0.3)
        try:
            # Clean possible markdown block
            clean = response.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            import json
            return json.loads(clean.strip())
        except Exception:
            # Fallback to candidate 1 if parse fails
            fallback = trends[0]
            return {
                "selected_title": fallback["title"],
                "core_breakthrough": fallback["summary"],
                "why_it_matters": "Fundamental shift in agentic and LLM efficiency.",
                "contrarian_take": "Most teams are optimizing prompts when they should be optimizing compute allocation.",
                "source_url": fallback["url"]
            }

trend_scout = TrendScoutAgent()
