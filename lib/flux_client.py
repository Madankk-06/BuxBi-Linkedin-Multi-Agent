import os
import time
import io
import urllib.parse
import logging
from pathlib import Path
from typing import Optional
import requests
from PIL import Image

from core.config import config
from lib.llm_client import llm_client

logger = logging.getLogger(__name__)

VISUAL_THEMES = [
    {
        "id": "bauhaus_editorial",
        "name": "Minimalist Bauhaus / Swiss Editorial",
        "aesthetic": "Minimalist Bauhaus graphic design, vector architecture of data flow, bold geometric shapes, clean flat composition, warm ivory cream background, deep cobalt blue and warm terracotta orange accents, high-end editorial tech magazine cover, crisp lines, no blur, no text"
    },
    {
        "id": "tactile_3d_clay",
        "name": "Tactile Matte 3D Claymation / Modular Isometric",
        "aesthetic": "High-end 3D clay render, tactile isometric modular blocks representing an AI system, soft diffuse daylight studio lighting, terracotta, sage green, and warm sandstone palette, matte ceramic textures, clean architectural layout, Cinema4D render, no text"
    },
    {
        "id": "scandinavian_studio",
        "name": "Scandinavian Studio / Light Wood & Brushed Metal",
        "aesthetic": "Modern Scandinavian product design, natural light blonde wood, brushed titanium, subtle soft shadows, airy off-white background, clean physical hardware metaphor for data systems, award-winning industrial design photography, no text"
    },
    {
        "id": "glassmorphic_prism",
        "name": "Glassmorphism / Frosted Holographic Prisms",
        "aesthetic": "Translucent frosted glass geometric slabs, subtle iridescent refraction of soft spectrum light, modern clean UI/UX layers floating in space, minimal soft-gray backdrop, elegant Apple design language, raytraced reflections, no text"
    },
    {
        "id": "cyber_blueprint",
        "name": "Precision Technical Schematic / Blue-line Drafting",
        "aesthetic": "Crisp technical drafting blueprint, deep Prussian blue background with clean white and amber schematic vector lines, laser-precise technical diagram aesthetic, architectural elevation drawing of data pipelines, no text"
    },
    {
        "id": "vintage_synth",
        "name": "Retro-Futurism / Vintage 1980s Hardware Manual",
        "aesthetic": "Vintage 1980s computer engineering manual illustration, risograph screenprint texture, subtle halftone dot patterns, muted mustard yellow, slate teal, and rust orange palette, analog synthesizer hardware aesthetic, no text"
    },
    {
        "id": "obsidian_neon",
        "name": "Cyber Obsidian / Sleek Volumetric Tech",
        "aesthetic": "Sleek dark obsidian monolithic blocks, vibrant electric magenta and cyan fiber-optic light pathways, clean volumetric depth, subtle atmospheric haze, high-contrast futuristic computing infrastructure, no text"
    }
]

class FluxImageEngine:
    def __init__(self):
        self.output_dir = config.DATA_DIR / "generated_cards"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_theme_index = 0

    def get_next_theme(self) -> dict:
        """Rotate to the next visual theme so images are never repetitive."""
        theme = VISUAL_THEMES[self.current_theme_index % len(VISUAL_THEMES)]
        self.current_theme_index += 1
        return theme

    def generate_image_for_post(self, post_id: int, topic: str, draft_text: str, theme_id: Optional[str] = None) -> tuple[str, str]:
        """Generate a creative, non-generic FLUX.1 image matching the post's context."""
        
        # 1. Select theme
        if theme_id:
            theme = next((t for t in VISUAL_THEMES if t["id"] == theme_id), self.get_next_theme())
        else:
            theme = self.get_next_theme()

        logger.info(f"Generating FLUX.1 visual with Theme: {theme['name']}")

        # 2. Prompt LLM to translate post context into an artistic physical metaphor
        llm_system = """
You are a World-Class Creative Art Director for high-end tech publications (like Wired, Stripe Press, and MIT Tech Review).
Your job is to translate a technical Generative AI concept into a compelling, conceptual physical art prompt.

RULES:
1. NEVER describe generic tropes (NO glowing human brains, NO robots typing on laptops, NO blue holographic earth, NO floating binary code 0101).
2. Use physical, spatial metaphors (e.g., modular interlocking blocks, prisms refracting light paths, layered monolithic architectures, kinetic pipelines, mechanical routing switches).
3. Do NOT include text inside the image.
4. Output ONLY the image prompt (max 50 words) with no intro or quotes.
"""
        user_prompt = f"""
Post Topic: {topic}
Key Architectural Concept in post:
{draft_text[:400]}

Visual Theme Aesthetic: {theme['aesthetic']}

Write the bespoke art prompt for FLUX.1 now:
"""
        art_prompt = llm_client.generate(user_prompt, system_prompt=llm_system, temperature=0.6).strip()
        # Clean quotes
        art_prompt = art_prompt.strip('"\'')
        final_prompt = f"{art_prompt}, {theme['aesthetic']}"

        # 3. Call FLUX.1 via Pollinations
        encoded = urllib.parse.quote(final_prompt)
        seed = int(time.time()) % 100000
        url = f"https://image.pollinations.ai/prompt/{encoded}?model=flux&width=1200&height=675&nologo=true&seed={seed}"

        # 4. Fetch with retry if rate-limited
        max_retries = 3
        img_content = None

        for attempt in range(max_retries):
            try:
                logger.info(f"FLUX request attempt {attempt+1} for Post #{post_id}...")
                resp = requests.get(url, timeout=40)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                    img_content = resp.content
                    break
                elif resp.status_code == 402:
                    logger.warning("Pollinations free limit hit. Waiting 20 seconds before retry...")
                    time.sleep(20)
                else:
                    logger.warning(f"Unexpected status {resp.status_code}: {resp.text[:100]}")
                    time.sleep(5)
            except Exception as e:
                logger.warning(f"Error fetching FLUX image: {e}")
                time.sleep(5)

        if not img_content:
            raise RuntimeError("Failed to generate FLUX image after retries.")

        # 5. Process image with Pillow (crop bottom 32px to ensure zero watermark)
        img = Image.open(io.BytesIO(img_content))
        w, h = img.size
        # Crop watermark banner at the very bottom
        cropped = img.crop((0, 0, w, h - 32))

        # 6. Save image
        filename = f"flux_post_{post_id}_{int(time.time())}.jpg"
        save_path = self.output_dir / filename
        cropped.save(save_path, "JPEG", quality=95)
        logger.info(f"FLUX image saved to {save_path}")

        return str(save_path), theme["name"]

flux_engine = FluxImageEngine()
