import random
from typing import Dict, List

class DomainDirector:
    """Manages diverse, cutting-edge Generative AI engineering domains to prevent repetitive content."""

    DOMAINS = [
        {
            "id": "rag_retrieval",
            "name": "Advanced RAG & Retrieval Architectures",
            "topics": [
                {
                    "concept": "Chunk Boundary Bleed vs Semantic Chunking",
                    "hook_angle": "Why 80% of RAG retrieval failures have nothing to do with embedding models",
                    "practical_insight": "Fixed 512-token chunking splits crucial sentences across vectors. Transitioning to late-chunking or proposition chunking preserves relationship context without inflating vector index size."
                },
                {
                    "concept": "GraphRAG vs Dense Vector Search",
                    "hook_angle": "Dense vector search answers 'where', Knowledge Graphs answer 'how'",
                    "practical_insight": "Vector similarity fails on multi-hop questions across disconnected documents. Combining vector search with a lightweight community-clustered knowledge graph drops retrieval hallucination by 40%."
                },
                {
                    "concept": "Hybrid Search: BM25 + Cross-Encoder Reranking",
                    "hook_angle": "The cheapest 2x accuracy upgrade in production search is not a bigger LLM",
                    "practical_insight": "Pure dense retrieval misses exact alphanumeric IDs and acronyms. Reciprocal Rank Fusion (RRF) combining sparse BM25 and dense bi-encoders, passed through a small cross-encoder reranker, outperforms expensive raw prompt stuffing."
                }
            ]
        },
        {
            "id": "vector_databases",
            "name": "Vector Databases & High-Scale Indexing",
            "topics": [
                {
                    "concept": "HNSW vs DiskANN Memory Economics",
                    "hook_angle": "The hidden RAM cost of vector databases when scaling past 10M vectors",
                    "practical_insight": "In-memory HNSW graphs can cost thousands in monthly cloud RAM. Disk-backed indexes with product quantization (PQ) slash memory requirements by 80% with less than 3% drop in recall."
                },
                {
                    "concept": "Metadata Pre-Filtering Bottlenecks",
                    "hook_angle": "Why post-filtering your vector queries is silently destroying your P99 latency",
                    "practical_insight": "Filtering 1M vectors after computing cosine distances wastes compute on discarded tokens. Single-stage filtered HNSW indexing avoids graph disconnection while keeping sub-15ms query budgets."
                }
            ]
        },
        {
            "id": "inference_optimization",
            "name": "LLM Inference Engineering & GPU Economics",
            "topics": [
                {
                    "concept": "KV Cache Quantization & PagedAttention",
                    "hook_angle": "The memory bottleneck in production LLMs is not weights—it's the KV cache",
                    "practical_insight": "At 32k context, a 70B model's KV cache consumes more GPU VRAM than the model weights. FP8 or INT4 KV quantization allows 3x larger batch sizes with imperceptible degradation in generation quality."
                },
                {
                    "concept": "Speculative Decoding in Production",
                    "hook_angle": "How to get 2.5x higher token generation speed without paying for a faster GPU",
                    "practical_insight": "Pairing a small 1B draft model with a 70B target model allows verified parallel decoding. Memory bandwidth is utilized effectively while retaining exact mathematical output of the larger model."
                },
                {
                    "concept": "Prompt Caching ROI in Agentic Workflows",
                    "hook_angle": "Why uncached system prompts are burning 60% of your API budget in multi-turn agents",
                    "practical_insight": "Structuring agent system prompts with static documentation prefixes enables 90% cache read discounts, slashing latency from 1.8s down to 350ms."
                }
            ]
        },
        {
            "id": "agentic_workflows",
            "name": "Autonomous Agents & Production Orchestration",
            "topics": [
                {
                    "concept": "Stateful Agent Graphs vs Blind ReAct Loops",
                    "hook_angle": "Why simple while-loop AI agents fail after step 4 in enterprise environments",
                    "practical_insight": "Unconstrained ReAct loops cascade early errors. Deterministic state machines with scoped fallback paths and deterministic schema checkpoints keep agent trajectories aligned."
                },
                {
                    "concept": "Evaluation Harnesses for Non-Deterministic Agents",
                    "hook_angle": "If you cannot evaluate your agents in CI/CD, you do not have production software",
                    "practical_insight": "Unit testing LLM outputs with exact string matching fails. Building LLM-as-a-judge rubric suites with synthetic ground truth enables reliable release cycles."
                }
            ]
        },
        {
            "id": "fine_tuning_distillation",
            "name": "Model Distillation, SLMs & Custom Fine-Tuning",
            "topics": [
                {
                    "concept": "Domain-Specific 8B Models vs General 70B Giants",
                    "hook_angle": "A properly distilled 8B model will crush a general 70B model on your private data",
                    "practical_insight": "Fine-tuning with curated high-signal synthetic reasoning chains produces an 8B model that executes domain tasks at 1/10th the latency and 1/15th the inference cost."
                },
                {
                    "concept": "Direct Preference Optimization (DPO) in Practice",
                    "hook_angle": "Why RLHF is dying for enterprise fine-tuning and DPO is winning",
                    "practical_insight": "DPO skips training an unstable separate reward model. Optimizing directly on preference pairs mathematically converges faster with zero policy collapse."
                }
            ]
        }
    ]

    def select_topic_brief(self) -> Dict:
        """Select a diverse topic across rotating Gen AI domains with rich practitioner angles."""
        domain = random.choice(self.DOMAINS)
        topic = random.choice(domain["topics"])
        return {
            "domain_id": domain["id"],
            "domain_name": domain["name"],
            "concept": topic["concept"],
            "hook_angle": topic["hook_angle"],
            "practical_insight": topic["practical_insight"]
        }

domain_director = DomainDirector()
