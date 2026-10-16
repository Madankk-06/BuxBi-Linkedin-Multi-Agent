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

    @staticmethod
    def clean_formatting(text: str) -> str:
        """Deterministically strip asterisks (*), markdown headers (#), and arrow symbols (↳) from any text."""
        if not text:
            return ""
        cleaned = text.strip()

        # Remove markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)

        # Replace arrow/fancy symbols with clean bullet point '•'
        for sym in ("↳", "→", "⇒", "▸", "▹", "➢", "➤", "➔", "➜"):
            cleaned = cleaned.replace(sym, "•")

        # Strip markdown heading markers at start of lines
        cleaned = re.sub(r"(?m)^#{1,6}\s+", "", cleaned)

        # Strip all asterisks (* and **)
        cleaned = cleaned.replace("**", "").replace("*", "")

        # Normalize multiple spaces (without collapsing newlines)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def audit_and_humanize(self, raw_draft: str) -> str:
        """Run an aggressive humanization scrub to eliminate AI markers, asterisks, and arrow symbols."""
        
        system_prompt = """
You are the Humanizer & Authenticity Auditor.
Your job is to rewrite the draft so it sounds like an experienced senior engineer sharing a practical lesson on LinkedIn over coffee.

STRICT EDITING RULES:
1. Strip all journalistic or academic news phrasing ("In recent developments", "Researchers have introduced").
2. Strip sterile AI corporate jargon (delve, leverage, foster, streamline, holistic, tapestry, multifaceted, crucial, notable).
3. Ensure natural, conversational flow. Avoid robotic symmetry and fake reveal bridges ("The result?", "Plot twist:").
4. Keep the sentence structure varied—some short punchy statements, some thoughtful explanations.
5. Preserve technical depth, exact terms, and metrics.
6. ABSOLUTELY NO ASTERISKS (* or **): Never use markdown asterisks anywhere.
7. ABSOLUTELY NO ARROW SYMBOLS (↳, →, ⇒): Replace any arrow symbols with standard bullet points ('•') or numbers ('1.', '2.').

Output ONLY the revised post text without commentary, quotes, or preamble.
"""
        prompt = f"Scrub and humanize this draft into an authentic, experienced engineer's voice:\n\n{raw_draft}"
        cleaned = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.35)
        
        final_text = self.clean_formatting(cleaned)

        # Scrub banned words
        for word in self.BANNED_WORDS:
            pattern = re.compile(rf"\b{word}\b", re.IGNORECASE)
            final_text = pattern.sub("use", final_text) if word in ("leverage", "harness") else pattern.sub("", final_text)

        final_text = re.sub(r"[ \t]+", " ", final_text)
        final_text = re.sub(r"\n{3,}", "\n\n", final_text)
        return final_text.strip()

humanizer = HumanizerAgent()
