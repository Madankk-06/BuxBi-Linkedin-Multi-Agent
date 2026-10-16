import json
import logging
from lib.llm_client import llm_client
from lib.image_client import image_client

logger = logging.getLogger(__name__)

class ImageArchitectAgent:
    """Designs professional multi-tier architecture diagrams and animated GIFs for LinkedIn."""

    def design_post_image(self, domain_name: str, title: str, post_draft: str) -> str:
        """Analyze the post content and render a multi-layer architecture diagram (PNG + Animated GIF)."""
        system_prompt = """
You are the Systems Architect and Visual Diagram Designer for top tech publications.
Analyze the provided LinkedIn post draft and generate a clean 5-6 layer architecture diagram schema for the topic.

Output strictly valid JSON with no markdown wrapping:
{
  "system_title": "Max 35 chars uppercase title (e.g. PRODUCTION RAG STACK SIMPLIFIED)",
  "system_subtitle": "Max 65 chars subtitle describing the ecosystem",
  "layers": [
    {
      "layer_number": 1,
      "name": "LAYER 1 NAME (e.g. INGESTION & EXTRACTION)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    },
    {
      "layer_number": 2,
      "name": "LAYER 2 NAME (e.g. EMBEDDINGS & CHUNKING)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    },
    {
      "layer_number": 3,
      "name": "LAYER 3 NAME (e.g. VECTOR STORAGE & INDEXING)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    },
    {
      "layer_number": 4,
      "name": "LAYER 4 NAME (e.g. RETRIEVAL & RERANKING)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    },
    {
      "layer_number": 5,
      "name": "LAYER 5 NAME (e.g. FOUNDATION MODELS & REASONING)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    },
    {
      "layer_number": 6,
      "name": "LAYER 6 NAME (e.g. EVALS & OBSERVABILITY)",
      "tools": ["Tool 1", "Tool 2", "Tool 3", "Tool 4"]
    }
  ],
  "takeaway": "Short golden rule / architectural maxim (max 85 chars)"
}
"""
        prompt = f"Domain: {domain_name}\nTitle: {title}\nPost Draft:\n{post_draft}\n\nGenerate the architecture diagram JSON:"
        
        try:
            resp = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.2).strip()
            if resp.startswith("```json"):
                resp = resp[7:]
            if resp.startswith("```"):
                resp = resp[3:]
            if resp.endswith("```"):
                resp = resp[:-3]
            data = json.loads(resp.strip())

            return image_client.generate_architecture_diagram(data, return_gif=True)
        except Exception as e:
            logger.warning(f"Failed to parse architecture schema, using fallback: {e}")
            fallback_data = {
                "system_title": f"{domain_name.upper()} STACK SIMPLIFIED",
                "system_subtitle": "Breaking down the end-to-end architecture into practical layers",
                "layers": [
                    {"layer_number": 1, "name": "INFRASTRUCTURE & COMPUTE", "tools": ["GPU Clusters", "vLLM", "TensorRT-LLM", "Triton"]},
                    {"layer_number": 2, "name": "DATA & STORAGE LAYER", "tools": ["Feature Store", "Blob Storage", "Embeddings"]},
                    {"layer_number": 3, "name": "CORE PROCESSING & PIPELINE", "tools": ["Chunking", "Tokenization", "Routing"]},
                    {"layer_number": 4, "name": "MODEL REASONING & INFERENCE", "tools": ["Claude 3.5", "GPT-4o", "Qwen 2.5", "DeepSeek"]},
                    {"layer_number": 5, "name": "MLOPS & GOVERNANCE", "tools": ["Guardrails", "Langfuse", "Telemetry", "Eval Harness"]}
                ],
                "takeaway": "The real skill is understanding which service belongs at each stage and how they connect."
            }
            return image_client.generate_architecture_diagram(fallback_data, return_gif=True)

image_architect = ImageArchitectAgent()
