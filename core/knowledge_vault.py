import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from core.config import config
from lib.llm_client import llm_client

logger = logging.getLogger(__name__)

VAULT_FILE = config.DATA_DIR / "knowledge_vault.json"

class KnowledgeVault:
    """Manages persistent ingestion of user-provided tech documents, notes, and frameworks,
    deeply analyzing them with outside technical context to drive first-principles LinkedIn posts.
    """

    def __init__(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = {
            "topics": [],
            "weekly_intimation_last_sent": None
        }
        self.load()

    def load(self):
        if VAULT_FILE.exists():
            try:
                with open(VAULT_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading knowledge vault: {e}")
                self.data = {"topics": [], "weekly_intimation_last_sent": None}

    def save(self):
        try:
            with open(VAULT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving knowledge vault: {e}")

    def ingest_document_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Extract text from PDF, Markdown, or TXT file and run deep technical ingestion."""
        ext = original_filename.lower().rsplit(".", 1)[-1] if "." in original_filename else "txt"
        extracted_text = ""

        if ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                pages_text = []
                for p in reader.pages[:20]:  # Up to 20 pages
                    t = p.extract_text()
                    if t:
                        pages_text.append(t)
                extracted_text = "\n".join(pages_text).strip()
            except Exception as e:
                logger.error(f"Error reading PDF file {file_path}: {e}")
                extracted_text = ""

        if not extracted_text:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted_text = f.read().strip()
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                extracted_text = ""

        if not extracted_text:
            return {
                "success": False,
                "error": "Could not extract readable text from the provided document."
            }

        return self.ingest_raw_text(extracted_text, source_name=original_filename)

    def ingest_raw_text(self, text: str, source_name: str = "User Notes") -> Dict[str, Any]:
        """Analyze raw text, list of tech names, or notes into deep architectural knowledge."""
        system_prompt = """
You are the Chief AI Systems Analyst and Knowledge Curator for Buxbi.
Your mission: Ingest technical documents, framework names, architectural notes, or research papers provided by the engineer (Madan).
You must analyze the content deeply, connect it with outside industry engineering context, and extract actionable, high-signal technical truth.

STRICT CONSTRAINTS:
1. No marketing fluff, no superficial buzzwords.
2. Focus on:
   - What fundamental problem this technology solves.
   - Core architectural mechanics (memory layouts, scheduling algorithms, kernel optimizations, vector indexing, attention variants).
   - Real-world trade-offs (latency vs accuracy, memory footprint, cold-start, operational complexity).
   - Concrete comparison with the incumbent standard.
3. Output strictly valid JSON matching this schema:
{
  "technologies": [
    {
      "name": "Technology or Architecture Name",
      "category": "Inference / RAG / Agent / Fine-Tuning / Hardware / Evaluation",
      "one_line_summary": "Crisp technical summary under 120 chars",
      "core_mechanics": "Detailed breakdown of how it works under the hood",
      "concrete_metrics_or_tradeoffs": "Real latency/memory/throughput numbers or key architectural trade-offs",
      "versus_incumbent": "How it compares directly against the incumbent solution"
    }
  ],
  "overall_takeaways": "2-3 sentences of practitioner takeaways"
}
"""
        prompt = f"Source: {source_name}\n\nDocument / Content:\n{text[:15000]}\n\nExtract and analyze the technical insights:"

        try:
            raw = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.2).strip()
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            parsed = json.loads(raw.strip())
        except Exception as e:
            logger.warning(f"Error parsing deep insights via LLM: {e}")
            parsed = {
                "technologies": [
                    {
                        "name": source_name[:40],
                        "category": "Gen AI Systems",
                        "one_line_summary": text[:100].replace("\n", " "),
                        "core_mechanics": text[:400].replace("\n", " "),
                        "concrete_metrics_or_tradeoffs": "Key engineering trade-offs and latency benchmarks.",
                        "versus_incumbent": "Next-generation optimization over conventional architectures."
                    }
                ],
                "overall_takeaways": "Ingested technical insights saved to active knowledge base."
            }

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added_names = []

        for item in parsed.get("technologies", []):
            entry = {
                "name": item.get("name", "Unknown Tech"),
                "category": item.get("category", "Gen AI Systems"),
                "summary": item.get("one_line_summary", ""),
                "mechanics": item.get("core_mechanics", ""),
                "tradeoffs": item.get("concrete_metrics_or_tradeoffs", ""),
                "comparison": item.get("versus_incumbent", ""),
                "source": source_name,
                "status": "new",
                "added_at": now_str
            }
            # Avoid duplicate topic names
            self.data["topics"] = [t for t in self.data.get("topics", []) if t.get("name") != entry["name"]]
            self.data["topics"].insert(0, entry)
            added_names.append(entry["name"])

        self.save()
        logger.info(f"Ingested {len(added_names)} technical topics into Knowledge Vault: {added_names}")

        return {
            "success": True,
            "added_count": len(added_names),
            "added_technologies": added_names,
            "takeaways": parsed.get("overall_takeaways", "")
        }

    def get_priority_topic(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest unposted user-provided technology topic."""
        for t in self.data.get("topics", []):
            if t.get("status") == "new":
                return t
        # If all used, return the newest one for refreshed angles
        if self.data.get("topics"):
            return self.data["topics"][0]
        return None

    def mark_topic_used(self, topic_name: str):
        """Mark a topic as published."""
        for t in self.data.get("topics", []):
            if t.get("name") == topic_name:
                t["status"] = "used_in_post"
                t["used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save()
                break

    def get_vault_summary(self) -> str:
        """Return human-readable summary of stored knowledge."""
        topics = self.data.get("topics", [])
        if not topics:
            return "Knowledge Vault is currently empty. Send me any document (.pdf, .txt, .md) or tech names to ingest!"
        lines = [f"📚 <b>Buxbi Knowledge Vault ({len(topics)} topics stored):</b>\n"]
        for i, t in enumerate(topics[:6], 1):
            status_emoji = "🆕" if t.get("status") == "new" else "✅"
            lines.append(f"{i}. {status_emoji} <b>{t.get('name')}</b> ({t.get('category')})\n   • {t.get('summary')}")
        return "\n".join(lines)

knowledge_vault = KnowledgeVault()
