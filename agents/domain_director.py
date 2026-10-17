import random
import logging
from datetime import datetime
from typing import Dict, List, Optional
from core.knowledge_vault import knowledge_vault

logger = logging.getLogger(__name__)

class DomainDirector:
    """Manages diverse, cutting-edge Generative AI engineering domains and 7-day rotating content pillars
    to prevent repetitive content and guarantee first-principles engineering quality.
    """

    WEEKDAY_PILLARS = {
        0: "Monday: Industry Breakthroughs & Emerging Tech Shifts",
        1: "Tuesday: Deep System Architecture & Dataflow (Infographic Day)",
        2: "Wednesday: Production Failure Modes & Engineering Fixes",
        3: "Thursday: Direct Framework & Latency Benchmarks (A vs B)",
        4: "Friday: Senior Engineering Design Patterns & Anti-Patterns",
        5: "Saturday: Weekend Builder Experiments & Emerging Tools",
        6: "Sunday: High-Level Engineering Philosophy & Cognitive Architectures"
    }

    DOMAINS = [
        {
            "id": "rag_retrieval",
            "name": "Advanced RAG & Retrieval Architectures",
            "topics": [
                {
                    "concept": "Chunk Boundary Bleed vs Semantic Proposition Chunking",
                    "hook_angle": "Why 80% of production RAG retrieval failures have nothing to do with embedding models",
                    "practical_insight": "Fixed 512-token chunking arbitrarily splits crucial semantic context. Late-chunking and proposition chunking preserve atomic relationships before vectorization, cutting retrieval misses by 35% without inflating vector index size."
                },
                {
                    "concept": "GraphRAG vs Dense Vector Search",
                    "hook_angle": "Dense vector search answers 'where', Knowledge Graphs answer 'how'",
                    "practical_insight": "Vector similarity matching fails catastrophically on multi-hop questions across disconnected documents. Combining dense vector search with hierarchical community-clustered knowledge graphs drops factual hallucination by 40%."
                },
                {
                    "concept": "Hybrid Search: BM25 + Cross-Encoder Reranking",
                    "hook_angle": "The cheapest 2x accuracy upgrade in production search is not a bigger LLM",
                    "practical_insight": "Pure dense retrieval misses exact alphanumeric SKU numbers and domain acronyms. Reciprocal Rank Fusion (RRF) combining sparse BM25 and dense bi-encoders, passed through a compact cross-encoder reranker, outperforms expensive raw prompt stuffing."
                },
                {
                    "concept": "Context Window Bloat & Needle-In-A-Haystack Degradation",
                    "hook_angle": "Just because a model has a 1M token context window does not mean you should fill it",
                    "practical_insight": "Effective reasoning degrades significantly when context exceeds 32k tokens due to attention dispersion. Selective pre-retrieval routing and KV-cache budget allocation maintain 98% recall while keeping token costs predictable."
                }
            ]
        },
        {
            "id": "inference_optimization",
            "name": "LLM Inference Engineering & GPU Economics",
            "topics": [
                {
                    "concept": "KV Cache Quantization & PagedAttention",
                    "hook_angle": "The primary memory bottleneck in production LLMs is not weights—it is the KV cache",
                    "practical_insight": "At 32k context, a 70B model's KV cache consumes more GPU VRAM than the model weights. FP8 or INT4 KV quantization combined with PagedAttention non-contiguous memory allocation allows 3x larger concurrency batch sizes with imperceptible quality loss."
                },
                {
                    "concept": "Speculative Decoding in Production Serving",
                    "hook_angle": "How to get 2.5x higher token generation speed without paying for a faster GPU cluster",
                    "practical_insight": "Pairing a small 1B draft model with a 70B target model allows verified parallel speculative token verification. Memory bandwidth memory-bound kernels are transformed into compute-bound operations, slashing time-to-first-token (TTFT) and inter-token latency (ITL)."
                },
                {
                    "concept": "Continuous Batching vs Static Request Batching",
                    "hook_angle": "Why naive GPU batching creates massive tail latency spikes in customer applications",
                    "practical_insight": "Waiting for the slowest sequence in a batch to finish wastes GPU execution cores. Iteration-level continuous scheduling (as in vLLM and TensorRT-LLM) evicts finished requests instantly, multiplying serving throughput by 4x."
                },
                {
                    "concept": "FlashAttention-3 & FP8 GEMM Matrix Kernels",
                    "hook_angle": "The physics of GPU memory bandwidth: Why algorithms must be hardware-aware",
                    "practical_insight": "Standard attention requires quadratic O(N^2) memory read/writes to high-bandwidth memory (HBM). FlashAttention tiles computation directly in on-chip SRAM, cutting memory bandwidth bottlenecks and unlocking sub-10ms per-token latencies on modern Hopper architecture."
                }
            ]
        },
        {
            "id": "agentic_workflows",
            "name": "Autonomous Agents & Production Orchestration",
            "topics": [
                {
                    "concept": "Stateful Agent Graphs vs Blind ReAct Loops",
                    "hook_angle": "Why simple while-loop AI agents fail after step 4 in enterprise production",
                    "practical_insight": "Unconstrained ReAct loops cascade early reasoning errors into catastrophic failure. Deterministic state machines with explicit cycle limits, typed schema validation, and isolated sub-agents keep execution trajectories grounded."
                },
                {
                    "concept": "Evaluation Harnesses for Non-Deterministic Agents",
                    "hook_angle": "If you cannot evaluate your agents in CI/CD, you do not have production software",
                    "practical_insight": "Unit testing LLM outputs with exact string matching is futile. Building LLM-as-a-judge rubric suites with synthetic ground truth and deterministic tool-call trajectory verification enables reliable release cycles."
                },
                {
                    "concept": "Tool Calling Protocol: Function Schemas vs Raw JSON Extraction",
                    "hook_angle": "How malformed JSON generation causes 60% of agent runtime crashes",
                    "practical_insight": "Using regex parsing on unstructured text outputs is fragile. Grammar-constrained decoding (outlines, instructor) forces the LLM's next-token logits to strictly follow JSON schema rules at zero inference latency penalty."
                }
            ]
        },
        {
            "id": "model_distillation",
            "name": "Model Distillation, SLMs & On-Device AI",
            "topics": [
                {
                    "concept": "Domain-Specific 8B Models vs General 70B Giants",
                    "hook_angle": "A properly distilled 8B model will crush a general 70B model on your private company data",
                    "practical_insight": "Fine-tuning with curated high-signal synthetic reasoning chains produces an 8B model that executes domain-specific tasks at 1/10th the latency and 1/15th the inference cost, all runnable on single-GPU hardware."
                },
                {
                    "concept": "BitNet b1.58 & 1-Bit LLM Architectures",
                    "hook_angle": "The end of floating-point multiplication: Why 1.58-bit models change everything",
                    "practical_insight": "Replacing matrix multiplication with pure integer addition (-1, 0, 1 ternary weights) slashes GPU/NPU energy consumption by 85% and allows 70B parameter models to fit into standard CPU memory."
                }
            ]
        }
    ]

    def __init__(self):
        self.recently_used_concepts: List[str] = []

    def select_topic_brief(self) -> Dict:
        """Select a diverse, high-impact topic.
        
        Priority 1: User-ingested knowledge from the Knowledge Vault (documents, tech names).
        Priority 2: Day-of-week rotating engineering pillar with anti-repetition guardrails.
        """
        # 1. Check if user provided fresh tech/documents in the Knowledge Vault
        priority = knowledge_vault.get_priority_topic()
        if priority and priority.get("status") == "new":
            name = priority.get("name")
            logger.info(f"Using user-ingested priority topic from Knowledge Vault: {name}")
            knowledge_vault.mark_topic_used(name)
            return {
                "domain_id": "user_knowledge",
                "domain_name": priority.get("category", "Gen AI Architecture"),
                "concept": name,
                "hook_angle": f"Deep architectural teardown: Why {name} matters for production AI systems",
                "practical_insight": f"{priority.get('summary')}. {priority.get('mechanics')} Key trade-offs: {priority.get('tradeoffs')} Direct comparison: {priority.get('comparison')}"
            }

        # 2. Day-of-week rotation
        weekday = datetime.now().weekday()
        pillar_title = self.WEEKDAY_PILLARS.get(weekday, "Engineering Deep Dive")
        logger.info(f"Active Content Pillar for today ({datetime.now().strftime('%A')}): {pillar_title}")

        # Filter out recently used concepts
        candidate_topics = []
        for domain in self.DOMAINS:
            for t in domain["topics"]:
                if t["concept"] not in self.recently_used_concepts:
                    candidate_topics.append((domain, t))

        if not candidate_topics:
            self.recently_used_concepts.clear()
            candidate_topics = [(d, t) for d in self.DOMAINS for t in d["topics"]]

        selected_domain, selected_topic = random.choice(candidate_topics)

        # Track to prevent repetition
        self.recently_used_concepts.append(selected_topic["concept"])
        if len(self.recently_used_concepts) > 8:
            self.recently_used_concepts.pop(0)

        return {
            "domain_id": selected_domain["id"],
            "domain_name": selected_domain["name"],
            "concept": selected_topic["concept"],
            "hook_angle": selected_topic["hook_angle"],
            "practical_insight": selected_topic["practical_insight"],
            "day_pillar": pillar_title
        }

domain_director = DomainDirector()
