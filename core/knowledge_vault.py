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

def extract_docx_text(file_path: str) -> str:
    """Extract clean text paragraphs from a Microsoft Word .docx file without external dependencies."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(file_path) as z:
            if "word/document.xml" in z.namelist():
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                    if texts:
                        clean_p = "".join(texts).strip()
                        if clean_p:
                            paragraphs.append(clean_p)
                return "\n".join(paragraphs).strip()
    except Exception as e:
        logger.error(f"Error extracting docx text from {file_path}: {e}")
    return ""


def extract_topic_items_from_text(text: str) -> List[str]:
    """Parse distinct topic titles from multi-line text or bulleted lists."""
    import re
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    cleaned = []
    ignore_prefixes = (
        "here are", "topics:", "pillar", "which of", "please analyze", "topic list",
        "i have pasted", "for /learn", "note:", "summary:"
    )
    for line in lines:
        c = re.sub(r"^[\s\d\.\-\*•\[\]\(\)\:\#]+", "", line).strip()
        if len(c) >= 3 and len(c) <= 120 and not c.lower().startswith(ignore_prefixes):
            cleaned.append(c)
    return cleaned


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
        """Extract text from Word (.docx), PDF, Markdown, or TXT file and run deep technical ingestion."""
        ext = original_filename.lower().rsplit(".", 1)[-1] if "." in original_filename else "txt"
        extracted_text = ""

        # Check if file has zip header (standard for .docx)
        is_zip = False
        try:
            with open(file_path, "rb") as bf:
                header = bf.read(4)
                if header == b"PK\x03\x04":
                    is_zip = True
        except Exception:
            pass

        # 1. Word Document (.docx)
        if ext in ("docx", "doc") or is_zip:
            extracted_text = extract_docx_text(file_path)

        # 2. PDF Document (.pdf)
        if not extracted_text and (ext == "pdf" or not is_zip):
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                pages_text = []
                for p in reader.pages[:30]:  # Up to 30 pages
                    t = p.extract_text()
                    if t:
                        pages_text.append(t)
                extracted_text = "\n".join(pages_text).strip()
            except Exception as e:
                logger.error(f"Error reading PDF file {file_path}: {e}")
                extracted_text = ""

        # 3. Plain Text / Markdown (.txt, .md, .json, .csv)
        if not extracted_text:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    extracted_text = f.read().strip()
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                extracted_text = ""

        # Reject raw unparsed binary fragments
        if extracted_text and (extracted_text.startswith("PK\x03\x04") or extracted_text.startswith("PK\u0003\u0004")):
            return {
                "success": False,
                "error": "The document could not be decompressed. Please ensure it is a valid .docx, .pdf, or .txt file."
            }

        if not extracted_text:
            return {
                "success": False,
                "error": "Could not extract readable text from the provided document."
            }

        return self.ingest_raw_text(extracted_text, source_name=original_filename)

    def ingest_raw_text(self, text: str, source_name: str = "User Notes") -> Dict[str, Any]:
        """Analyze raw text, list of tech names, or notes into deep architectural knowledge."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        candidate_topics = extract_topic_items_from_text(text)

        technologies = []
        overall_takeaways = ""

        # Case 1: Discrete list of multiple topics (e.g., 2+ topics)
        if len(candidate_topics) >= 2:
            logger.info(f"Detected {len(candidate_topics)} discrete topics to ingest from {source_name}")
            # Process in small batches of up to 4 so Groq produces deep, high-fidelity JSON without token cutoff
            batch_size = 4
            for i in range(0, len(candidate_topics), batch_size):
                batch = candidate_topics[i:i + batch_size]
                topics_prompt_list = "\n".join([f"- {t}" for t in batch])
                prompt = (
                    f"Source: {source_name}\n\n"
                    f"Analyze each of these specific technical topics deeply for production Gen AI architecture:\n"
                    f"{topics_prompt_list}\n\n"
                    f"STRICT INSTRUCTION: Output valid JSON with 'technologies' containing an analysis object for EACH of the {len(batch)} topics above."
                )
                system_prompt = """
You are the Chief AI Systems Analyst for Buxbi.
For each technical topic provided, extract deep engineering insight with ZERO marketing fluff.
Output strictly valid JSON matching this schema:
{
  "technologies": [
    {
      "name": "Exact Technology / Topic Name",
      "category": "Inference / RAG / Agents / Architecture / Evaluation / Security / Economics",
      "one_line_summary": "Crisp technical summary under 120 chars",
      "core_mechanics": "Deep breakdown of how it works under the hood (memory, latency, kernels, graph structures)",
      "concrete_metrics_or_tradeoffs": "Real latency/memory/throughput numbers or key architectural trade-offs",
      "versus_incumbent": "How it compares directly against the incumbent solution"
    }
  ],
  "overall_takeaways": "1-2 sentences of key engineering takeaways"
}
"""
                try:
                    raw = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.2, max_tokens=1800).strip()
                    if raw.startswith("```json"):
                        raw = raw[7:]
                    if raw.startswith("```"):
                        raw = raw[3:]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                    parsed = json.loads(raw.strip())
                    batch_techs = parsed.get("technologies", [])
                    technologies.extend(batch_techs)
                    if not overall_takeaways and parsed.get("overall_takeaways"):
                        overall_takeaways = parsed.get("overall_takeaways")
                except Exception as e:
                    logger.warning(f"Error parsing batch LLM insights ({e}), creating structured fallbacks for batch: {batch}")
                    for t in batch:
                        technologies.append({
                            "name": t,
                            "category": "Gen AI Architecture",
                            "one_line_summary": f"Production architecture and engineering considerations for {t}.",
                            "core_mechanics": f"Detailed architectural evaluation and implementation patterns of {t} in production systems.",
                            "concrete_metrics_or_tradeoffs": "Trade-offs between computational overhead, latency budgets, and system reliability.",
                            "versus_incumbent": "Offers modern decoupled design over legacy monolithic implementations."
                        })

            # Ensure any topic that was omitted by the LLM in batch responses still gets an entry
            existing_names = {item.get("name", "").lower() for item in technologies}
            for t in candidate_topics:
                if t.lower() not in existing_names:
                    technologies.append({
                        "name": t,
                        "category": "Gen AI Architecture",
                        "one_line_summary": f"Deep engineering teardown of {t}.",
                        "core_mechanics": f"Core mechanics and production tradeoffs for {t}.",
                        "concrete_metrics_or_tradeoffs": "Latency, throughput, and memory scaling bounds.",
                        "versus_incumbent": "Modern scalable alternative to standard architectures."
                    })
            if not overall_takeaways:
                overall_takeaways = f"Ingested {len(candidate_topics)} high-impact AI topics into active knowledge queue."

        # Case 2: Narrative text or single topic
        else:
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
      "category": "Inference / RAG / Agents / Architecture / Evaluation / Security / Economics",
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
                raw = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.2, max_tokens=1800).strip()
                if raw.startswith("```json"):
                    raw = raw[7:]
                if raw.startswith("```"):
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                parsed = json.loads(raw.strip())
                technologies = parsed.get("technologies", [])
                overall_takeaways = parsed.get("overall_takeaways", "")
            except Exception as e:
                logger.warning(f"Error parsing deep insights via LLM: {e}")
                technologies = [
                    {
                        "name": source_name[:40] if source_name != "User Notes" else text[:40].strip(),
                        "category": "Gen AI Systems",
                        "one_line_summary": text[:100].replace("\n", " "),
                        "core_mechanics": text[:400].replace("\n", " "),
                        "concrete_metrics_or_tradeoffs": "Key engineering trade-offs and latency benchmarks.",
                        "versus_incumbent": "Next-generation optimization over conventional architectures."
                    }
                ]
                overall_takeaways = "Ingested technical insights saved to active knowledge base."

        # Add all new entries to self.data["topics"] preserving order!
        added_names = []
        for item in technologies:
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
            # Remove any older instance of this exact topic name
            self.data["topics"] = [t for t in self.data.get("topics", []) if t.get("name").lower() != entry["name"].lower()]
            # Append so they are queued sequentially in the order given!
            self.data["topics"].append(entry)
            added_names.append(entry["name"])

        self.save()
        logger.info(f"Ingested {len(added_names)} technical topics into Knowledge Vault: {added_names}")

        return {
            "success": len(added_names) > 0,
            "added_count": len(added_names),
            "added_technologies": added_names,
            "takeaways": overall_takeaways
        }

    def get_priority_topic(self) -> Optional[Dict[str, Any]]:
        """Retrieve the next unposted user-provided technology topic."""
        for t in self.data.get("topics", []):
            if t.get("status") == "new":
                return t
        # If all used, return the newest one for refreshed angles
        if self.data.get("topics"):
            return self.data[-1]
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
            return "Knowledge Vault is currently empty. Send me any document (.docx, .pdf, .txt, .md) or tech names to ingest!"
        new_count = sum(1 for t in topics if t.get("status") == "new")
        used_count = len(topics) - new_count
        lines = [f"📚 <b>Buxbi Knowledge Vault ({len(topics)} topics: {new_count} new, {used_count} posted):</b>\n"]
        for i, t in enumerate(topics[:12], 1):
            status_emoji = "🆕" if t.get("status") == "new" else "✅"
            lines.append(f"{i}. {status_emoji} <b>{t.get('name')}</b> ({t.get('category')})\n   • {t.get('summary')}")
        if len(topics) > 12:
            lines.append(f"\n<i>...and {len(topics) - 12} more topics queued for upcoming posts!</i>")
        return "\n".join(lines)

knowledge_vault = KnowledgeVault()
