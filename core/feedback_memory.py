import os
import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

FEEDBACK_FILE = Path("data/feedback_rules.json")

# Core architectural rules learned from user feedback
DEFAULT_RULES = [
    "Nuance over absolute claims: Avoid implying pre-filtering always saves compute. Acknowledge engineering trade-offs between pre-filtering, integrated filtering, and post-filtering based on selectivity and recall requirements.",
    "Realistic benchmarks: Present latency metrics (such as 15ms or p99) as benchmarks or targets to measure against, not as universal guarantees.",
    "Graph mechanics: When discussing filtered HNSW or graph retrieval, explain that graph connectivity must be preserved during filtered traversal to prevent disconnected components.",
    "Measured downstream claims: Describe hallucination reduction as a possible downstream benefit of cleaner context, rather than a guaranteed fix.",
    "Pragmatic phrasing: Use 'optimize metadata filtering and reduce unnecessary computation' instead of exaggerated claims like 'solve the compute waste'.",
    "Formatting rules: Zero asterisks (* or **) anywhere in the text. Zero arrow symbols (↳, →, ⇒). Use standard numbers (1., 2., 3.) for main layers and clean bullet points (•) for sub-points."
]

class FeedbackMemory:
    """Persistent memory engine that stores user corrections, critiques, and lessons
    and injects them into Buxbi's generation and humanizing agents so mistakes are never repeated."""

    def __init__(self):
        self.rules: List[str] = list(DEFAULT_RULES)
        self.load_rules()

    def load_rules(self):
        try:
            if FEEDBACK_FILE.exists():
                with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, list):
                        # Merge saved rules with defaults without duplicates
                        for r in saved:
                            if r not in self.rules:
                                self.rules.append(r)
            else:
                self.save_rules()
        except Exception as e:
            logger.warning(f"Could not load feedback rules: {e}")

    def save_rules(self):
        try:
            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save feedback rules: {e}")

    def add_rule(self, rule_text: str) -> str:
        clean_rule = rule_text.strip()
        if not clean_rule:
            return ""
        if clean_rule not in self.rules:
            self.rules.append(clean_rule)
            self.save_rules()
            logger.info(f"Learned new rule from user: {clean_rule}")
        return clean_rule

    def get_rules_prompt(self) -> str:
        """Formatted rules block ready to inject into agent system prompts."""
        if not self.rules:
            return ""
        lines = [f"{i+1}. {rule}" for i, rule in enumerate(self.rules)]
        return (
            "CRITICAL LEARNED RULES FROM USER FEEDBACK (NEVER VIOLATE):\n"
            + "\n".join(lines)
            + "\n"
        )

feedback_memory = FeedbackMemory()
