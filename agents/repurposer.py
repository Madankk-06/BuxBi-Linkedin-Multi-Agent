import re
import logging
import requests
from typing import Tuple, Optional
from html.parser import HTMLParser
from lib.llm_client import llm_client
from agents.humanizer import humanizer
from core.feedback_memory import feedback_memory

logger = logging.getLogger(__name__)

class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.ignore_tag = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'noscript', 'svg'):
            self.ignore_tag = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'nav', 'header', 'footer', 'noscript', 'svg'):
            self.ignore_tag = False

    def handle_data(self, data):
        if not self.ignore_tag:
            clean = data.strip()
            if clean:
                self.text_parts.append(clean)

    def get_text(self):
        return " ".join(self.text_parts)


class RepurposerAgent:
    """Repurposes cross-platform content (articles, blogs, tweets, notes, or URLs) 
    into native, high-authority LinkedIn posts following the winning practitioner framework."""

    def extract_content(self, input_text: str) -> Tuple[str, str]:
        """Detect if input is a URL or raw text; fetch webpage if URL, else return text."""
        url_match = re.search(r'(https?://[^\s]+)', input_text.strip())
        if url_match:
            url = url_match.group(1)
            logger.info(f"Repurposer fetching external URL: {url}")
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                }
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200:
                    parser = SimpleHTMLTextExtractor()
                    parser.feed(resp.text)
                    extracted = parser.get_text()
                    title_match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE | re.DOTALL)
                    page_title = title_match.group(1).strip() if title_match else url
                    # Limit to ~4000 chars of extracted text
                    content_slice = extracted[:4000]
                    return f"Repurposed from: {page_title[:60]}", content_slice
            except Exception as e:
                logger.warning(f"Failed to fetch content from URL {url}: {e}")
        
        # Fallback to direct raw text
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]
        first_line = lines[0] if lines else "Repurposed Insights"
        title = first_line[:60]
        return f"Repurposed: {title}", input_text[:4000]

    def repurpose(self, raw_input: str) -> Tuple[str, str, str]:
        """Converts raw input/URL into a structured, humanized LinkedIn post.
        Returns: (topic_title, formula, final_draft)"""
        topic_title, source_content = self.extract_content(raw_input)
        rules_block = feedback_memory.get_rules_prompt()

        system_prompt = f"""
You are the Repurposer Specialist Agent for an executive-tier LinkedIn presence in Generative AI and software architecture.
Your mission is to take raw cross-platform content (articles, blog posts, video notes, X threads, or architectural memos)
and convert them into a punchy, high-authority native LinkedIn post.

{rules_block}

PROVEN LINKEDIN WINNING STRUCTURE:
1. Hook (Lines 1-2):
   A crisp, contrarian or architectural insight that grabs attention immediately.
   Example:
   "Most teams treat [concept] as an afterthought.
   Here is what actually changes when you structure the architecture properly:"

2. Structured Breakdown / Core Takeaways:
   Break the source material into 4-5 numbered pillars (1., 2., 3., 4.) or architectural tiers.
   Use ONLY standard bullet points ('•' or '-') for technical sub-points.

3. The Golden Rule / Executive Takeaway:
   1-2 sentences summarizing the overarching engineering or business truth.

4. Engaging Discussion Question:
   A thoughtful closing question inviting peers to share their experiences or approach.

STRICT WRITING RULES:
- ABSOLUTELY ZERO ASTERISKS (* or **): Never use markdown asterisks.
- ABSOLUTELY ZERO ARROW SYMBOLS (↳, →, ⇒): Use ONLY numbers (1., 2., 3.) and standard bullet points (•).
- Spacing: 1-2 sentence paragraphs with clean blank line breaks. Optimized for mobile scrolling.
- Tonality: Senior practitioner, objective, confident, educational.
- Target Length: 900 to 1,300 characters.
"""

        prompt = f"""
Transform the following source content into a native LinkedIn post:

SOURCE CONTENT:
{source_content}

Draft the post following the 4-part structure (Hook -> Numbered Breakdown with '•' bullets -> Golden Rule -> Discussion Question).
Ensure ZERO asterisks (*) and ZERO arrow symbols (↳). Write the post now:
"""

        raw_draft = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.5)
        # Apply the humanizer pass for buzzword removal and deterministic symbol scrub
        final_draft = humanizer.audit_and_humanize(raw_draft)
        formula = "Repurposed/Framework-Extraction"

        return topic_title, formula, final_draft

repurposer = RepurposerAgent()
