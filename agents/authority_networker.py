import json
import logging
from lib.llm_client import llm_client
from core.database import db

logger = logging.getLogger(__name__)

class AuthorityNetworkerAgent:
    """Finds high-authority Gen AI personas and crafts bespoke, high-converting connection request notes (<300 chars)."""

    CURATED_TARGET_PROFILES = [
        {
            "name": "Harrison Chase",
            "title": "Co-Founder & CEO",
            "company": "LangChain",
            "profile_url": "https://www.linkedin.com/in/harrison-chase-96611688/",
            "anchor": "Advancing agent cognitive architectures, evaluation harnesses, and tool orchestration in production."
        },
        {
            "name": "Chip Huyen",
            "title": "Author & AI Engineer",
            "company": "Designing Machine Learning Systems",
            "profile_url": "https://www.linkedin.com/in/chiphuyen/",
            "anchor": "Production ML systems engineering, streaming data pipelines, and real-time LLM inference trade-offs."
        },
        {
            "name": "Swyx (Shawn Wang)",
            "title": "Founder",
            "company": "Latent Space / Smarter.codes",
            "profile_url": "https://www.linkedin.com/in/shawnswyxwang/",
            "anchor": "AI Engineer movement, reverse-engineering test-time compute scaling, and open-weights model evals."
        },
        {
            "name": "Tri Dao",
            "title": "Chief Scientist & Assistant Professor",
            "company": "Together AI / Princeton",
            "profile_url": "https://www.linkedin.com/in/tri-dao/",
            "anchor": "FlashAttention architecture, memory-bandwidth optimizations, and state-space models (Mamba)."
        },
        {
            "name": "Jim Fan",
            "title": "Senior Research Scientist & Lead",
            "company": "NVIDIA",
            "profile_url": "https://www.linkedin.com/in/drjimfan/",
            "anchor": "Embodied AI, foundation models for robotics, and autonomous agent simulation environments."
        }
    ]

    def generate_daily_leads(self, count: int = 3) -> list[dict]:
        """Generate high-authority connection candidates with custom notes under 300 characters."""
        leads = []
        
        for candidate in self.CURATED_TARGET_PROFILES[:count]:
            note = self._craft_connection_note(candidate["name"], candidate["title"], candidate["anchor"])
            
            lead_data = {
                "name": candidate["name"],
                "title": candidate["title"],
                "company": candidate["company"],
                "profile_url": candidate["profile_url"],
                "why_relevant": candidate["anchor"],
                "customized_note": note
            }
            
            # Save to database
            db.save_connection_lead(
                candidate["name"], candidate["title"], candidate["company"],
                candidate["profile_url"], candidate["anchor"], note
            )
            leads.append(lead_data)

        return leads

    def _craft_connection_note(self, name: str, title: str, anchor: str) -> str:
        """Craft a personalized note strictly under 300 characters."""
        system_prompt = """
You craft high-converting, intellectual-peer LinkedIn connection notes for senior Gen AI leaders.

CONSTRAINTS:
1. STRICT CEILING: Note MUST be strictly under 300 characters (including spaces).
2. NO generic flattery (e.g., "I came across your profile and was impressed").
3. NO pitching, selling, or asking for 15-minute calls.
4. Anchor directly to their specific technical contribution or architecture domain.
5. Conversational, direct, respectful peer tone.
"""
        prompt = f"""
Candidate: {name}
Role: {title}
Technical Focus: {anchor}

Write a high-converting connection note under 300 characters:
"""
        raw_note = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.5).strip()
        
        # Clean quotes
        clean_note = raw_note.strip('"').strip("'").strip()
        
        # Guardrail: strictly enforce 300 character limit
        if len(clean_note) > 300:
            clean_note = clean_note[:297] + "..."
            
        return clean_note

authority_networker = AuthorityNetworkerAgent()
