import random
import logging
from typing import Optional
from lib.llm_client import llm_client
from agents.humanizer import humanizer
from core.database import db

logger = logging.getLogger(__name__)

class AuthorityNetworkerAgent:
    """Finds high-authority Gen AI personas and crafts bespoke, high-converting connection request notes (<300 chars)."""

    CURATED_TARGET_PROFILES = [
        {
            "name": "Harrison Chase",
            "title": "Co-Founder and CEO",
            "company": "LangChain",
            "profile_url": "https://www.linkedin.com/in/harrison-chase-96611688/",
            "anchor": "Advancing agent cognitive architectures, evaluation harnesses, and stateful LangGraph orchestration in production."
        },
        {
            "name": "Jerry Liu",
            "title": "Co-Founder and CEO",
            "company": "LlamaIndex",
            "profile_url": "https://www.linkedin.com/in/jerry-liu-64390071/",
            "anchor": "Enterprise RAG pipelines, document parsing architectures, and agentic document workflows."
        },
        {
            "name": "Chip Huyen",
            "title": "AI Systems Author and Founder",
            "company": "Claypot AI",
            "profile_url": "https://www.linkedin.com/in/chiphuyen/",
            "anchor": "Production ML systems engineering, streaming data pipelines, and real-time LLM inference trade-offs."
        },
        {
            "name": "Bob van Luijt",
            "title": "Co-Founder and CEO",
            "company": "Weaviate",
            "profile_url": "https://www.linkedin.com/in/bobvanluijt/",
            "anchor": "Vector database indexing, HNSW memory quantization, and hybrid search retrieval at scale."
        },
        {
            "name": "Qdrant / Andre Zayarni",
            "title": "Co-Founder and CEO",
            "company": "Qdrant",
            "profile_url": "https://www.linkedin.com/in/andrezayarni/",
            "anchor": "High-performance Rust vector search engines, single-stage filtered HNSW, and sparse-dense hybrid retrieval."
        },
        {
            "name": "Joao Moura",
            "title": "Founder and CEO",
            "company": "CrewAI",
            "profile_url": "https://www.linkedin.com/in/joaomdmoura/",
            "anchor": "Multi-agent role orchestration, autonomous task delegation, and enterprise agent workflows."
        },
        {
            "name": "Swyx (Shawn Wang)",
            "title": "Founder",
            "company": "Latent Space / AI Engineer",
            "profile_url": "https://www.linkedin.com/in/shawnswyxwang/",
            "anchor": "AI Engineer stack evolution, test-time compute scaling, and production agentic engineering."
        },
        {
            "name": "Tri Dao",
            "title": "Chief Scientist",
            "company": "Together AI / Princeton",
            "profile_url": "https://www.linkedin.com/in/tri-dao/",
            "anchor": "FlashAttention kernels, GPU memory-bandwidth optimization, and state-space models."
        },
        {
            "name": "Jim Fan",
            "title": "Senior Research Scientist and Lead",
            "company": "NVIDIA",
            "profile_url": "https://www.linkedin.com/in/drjimfan/",
            "anchor": "Foundation models for embodied AI, multimodal reasoning agents, and simulation scaling laws."
        },
        {
            "name": "Hamel Husain",
            "title": "Principal AI Engineer",
            "company": "Parlance Labs",
            "profile_url": "https://www.linkedin.com/in/hamelhusain/",
            "anchor": "Pragmatic LLM evaluation pipelines, domain-specific error analysis, and fine-tuning vs RAG trade-offs."
        },
        {
            "name": "Eugene Yan",
            "title": "Senior Applied Scientist",
            "company": "Amazon",
            "profile_url": "https://www.linkedin.com/in/eugeneyan/",
            "anchor": "LLM-powered recommender systems, alignment patterns, and production guardrails."
        },
        {
            "name": "Philipp Schmid",
            "title": "Technical Lead",
            "company": "Hugging Face",
            "profile_url": "https://www.linkedin.com/in/philipp-schmid-a6a2bb196/",
            "anchor": "Open-weights LLM deployment, quantization benchmarks, and production inference optimization."
        }
    ]

    def generate_daily_leads(self, count: int = 3, topic_hint: Optional[str] = None) -> list[dict]:
        """Generate high-authority connection candidates with custom notes under 300 characters."""
        leads = []
        pool = list(self.CURATED_TARGET_PROFILES)
        random.shuffle(pool)

        # If topic_hint is available, prioritize candidates whose anchor shares keywords
        if topic_hint:
            keywords = [w.lower() for w in topic_hint.split() if len(w) > 3]
            pool.sort(
                key=lambda c: sum(1 for kw in keywords if kw in c["anchor"].lower() or kw in c["company"].lower()),
                reverse=True
            )

        selected = pool[:count]

        for candidate in selected:
            note = self._craft_connection_note(
                candidate["name"],
                candidate["title"],
                candidate["company"],
                candidate["anchor"]
            )
            
            lead_data = {
                "name": candidate["name"],
                "title": candidate["title"],
                "company": candidate["company"],
                "profile_url": candidate["profile_url"],
                "why_relevant": candidate["anchor"],
                "customized_note": note
            }
            
            # Save to database
            try:
                db.save_connection_lead(
                    candidate["name"], candidate["title"], candidate["company"],
                    candidate["profile_url"], candidate["anchor"], note
                )
            except Exception as e:
                logger.warning(f"Could not save connection lead to DB: {e}")

            leads.append(lead_data)

        return leads

    def _craft_connection_note(self, name: str, title: str, company: str, anchor: str) -> str:
        """Craft a personalized note strictly under 300 characters without asterisks or symbols."""
        system_prompt = """
You craft high-converting, intellectual-peer LinkedIn connection notes from Madan (a Gen AI Developer) to senior Gen AI leaders.

CONSTRAINTS:
1. STRICT CEILING: Note MUST be strictly under 280 characters (including spaces).
2. NO generic flattery (e.g., "I came across your profile and was impressed").
3. NO pitching, selling, or asking for 15-minute calls.
4. Anchor directly to their specific technical contribution or architecture domain.
5. Conversational, direct, respectful peer tone.
6. ABSOLUTELY NO ASTERISKS (* or **) and NO ARROW SYMBOLS (↳). Plain natural sentences only.
"""
        prompt = f"""
Candidate: {name} ({title} at {company})
Technical Focus: {anchor}

Write a single personalized LinkedIn connection note under 280 characters (plain text only, no quotes, no asterisks):
"""
        try:
            raw_note = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.5).strip()
        except Exception as e:
            logger.warning(f"LLM fallback for connection note: {e}")
            raw_note = (
                f"Hi {name.split()[0]}, I have been building production Gen AI systems and closely following your work at {company} on {anchor[:80].lower()}. "
                f"Would love to connect and follow your engineering updates."
            )

        # Clean formatting, quotes, asterisks, and symbols
        clean_note = humanizer.clean_formatting(raw_note).strip('"').strip("'").strip()
        clean_note = clean_note.replace("\n", " ")

        # Guardrail: strictly enforce 300 character limit
        if len(clean_note) > 295:
            clean_note = clean_note[:292] + "..."

        return clean_note

authority_networker = AuthorityNetworkerAgent()
