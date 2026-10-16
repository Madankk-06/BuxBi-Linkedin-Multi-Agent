import re
import logging
from lib.llm_client import llm_client

logger = logging.getLogger(__name__)

class HumanizerAgent:
    BANNED_WORDS = [
        "delve", "tapestry", "realm", "pivotal", "testament", "beacon", "harness", 
        "foster", "streamline", "multifaceted", "holistic", "elevate", "game-changer",
        "revolutionary", "revolutionize", "unleash", "demystify", "furthermore", "moreover",
        "in conclusion", "it is important to remember", "exciting", "remarkable"
    ]

    NEWS_CLICHES = [
        r"In recent years", r"In today's fast-paced", r"Researchers have",
        r"A recent study", r"In the ever-evolving world of", r"The landscape of AI"
    ]

    def audit_and_humanize(self, raw_draft: str) -> str:
        """Run an aggressive humanization scrub to eliminate AI markers and news clichés."""
        
        system_prompt = """
You are the Humanizer & Authenticity Auditor.
Your job is to rewrite the draft so it sounds like an experienced senior engineer sharing a practical lesson on LinkedIn over coffee.

STRICT EDITING RULES:
1. Strip all journalistic or academic news phrasing ("In recent developments", "Researchers have introduced").
2. Strip sterile AI corporate jargon (delve, leverage, foster, streamline, holistic, tapestry, multifaceted, crucial, notable).
3. Ensure natural, conversational flow. Avoid robotic symmetry and fake reveal bridges ("The result?", "Plot twist:").
4. Keep the sentence structure varied—some short punchy statements, some thoughtful explanations.
5. Preserve technical depth, exact terms, and metrics.
6. ABSOLUTELY NO ASTERISKS (* or **): Never use markdown asterisks anywhere. LinkedIn displays raw asterisks as literal characters. Use clean uppercase headers or unicode '↳' and '•'.

Output ONLY the revised post text without commentary, quotes, or preamble.
"""
        prompt = f"Scrub and humanize this draft into an authentic, experienced engineer's voice:\n\n{raw_draft}"
        cleaned = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.35)
        
        final_text = cleaned.strip()
        
        # Remove any markdown code block wrappers
        if final_text.startswith("```"):
            final_text = re.sub(r"^```[a-zA-Z]*\n", "", final_text)
            final_text = re.sub(r"\n```$", "", final_text)

        # Strip all asterisks (* and **)
        final_text = final_text.replace("**", "").replace("*", "")

        # Scrub banned words
        for word in self.BANNED_WORDS:
            pattern = re.compile(rf"\b{word}\b", re.IGNORECASE)
            final_text = pattern.sub("use", final_text) if word in ("leverage", "harness") else pattern.sub("", final_text)

        # Normalize spaces and blank lines
        final_text = re.sub(r" +", " ", final_text)
        final_text = re.sub(r"\n{3,}", "\n\n", final_text)
        return final_text.strip()

humanizer = HumanizerAgent()
