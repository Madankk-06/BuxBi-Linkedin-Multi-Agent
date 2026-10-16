import logging
from lib.llm_client import llm_client
from core.feedback_memory import feedback_memory

logger = logging.getLogger(__name__)

class PostArchitectAgent:
    def draft_post(self, brief: dict) -> tuple[str, str]:
        """Draft an authoritative, layer-by-layer ecosystem breakdown Gen AI LinkedIn post."""
        
        rules_block = feedback_memory.get_rules_prompt()

        system_prompt = f"""
You are the Post Architect Agent for an executive-tier LinkedIn presence in Generative AI.
Your mission is to write high-authority, systematic architectural breakdown posts that simplify complex Gen AI ecosystems into clear, digestible engineering layers.

{rules_block}

PROVEN WINNING FORMULA (Ecosystem Simplified Framework):
1. Empathy Hook (Lines 1-2):
   "[Technology / Domain] can feel overwhelming.
   But once you break the ecosystem into layers, the architecture becomes much easier to understand."

2. Systematic Layer-by-Layer Walkthrough:
   Walk through 5-6 numbered architectural tiers (1., 2., 3., 4., 5.) with real-world tools, frameworks, and techniques.
   For sub-points under a tier, use ONLY standard bullet points ('•' or '-'):
   "The Core Retrieval Engine handles:
   • Dense vector search
   • Sparse BM25 keyword matching
   • Cross-encoder reranking
   • Context compression"

3. Architectural Maxim / Golden Rule:
   "The real skill is not memorizing [tool names].
   It is understanding which component belongs at each stage of the pipeline and how they connect together."

4. Peer-Level Discussion Question:
   A clean question inviting engineers and architects to share their current focus:
   "Which part of this stack are you building or optimizing right now?"

TONALITY & FORMATTING RULES:
- Objective, educational, authoritative, and clean.
- NO forced personal stories ("I spent 3 weeks...", "We killed our loop...").
- NO dry news reporting ("Researchers at Stanford published a paper...").
- ABSOLUTELY NO ASTERISKS (* or **): Never use markdown asterisks anywhere in the post.
- ABSOLUTELY NO ARROW SYMBOLS (↳, →, ⇒, ▸, ➤): Never use '↳' or arrow symbols. Use ONLY numbers (1., 2., 3.) and standard bullet points (•).
- Spacing: 1-2 sentence paragraphs with clean blank line breaks. Optimized for mobile readability.
- Length: 900 to 1,300 characters.
"""

        prompt = f"""
Write a LinkedIn architectural breakdown post based on this Gen AI topic:

Domain: {brief.get('domain_name')}
Core Concept: {brief.get('concept')}
Practical Angle: {brief.get('practical_insight')}

Follow the Ecosystem Simplified structure strictly:
1. Hook: "{brief.get('concept')} can feel overwhelming..."
2. Numbered layer-by-layer breakdown (1. Infrastructure/Ingestion, 2. Processing, 3. Core Engine with '•' bullet points, 4. Models/Reasoning, 5. Production/Monitoring).
3. The golden rule / architectural maxim.
4. The engaging closing question.

Remember: Follow all learned rules strictly. ZERO asterisks (*), ZERO arrow symbols (↳). Use only numbers (1., 2., 3.) and standard bullet points (•).
Write the post now:
"""

        draft = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.5)
        return "Ecosystem-Simplified/Layered-Breakdown", draft

post_architect = PostArchitectAgent()
