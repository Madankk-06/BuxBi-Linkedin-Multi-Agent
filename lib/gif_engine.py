#!/usr/bin/env python3
"""
LinkedIn Architecture GIF Generator (Production Engine v4.0)
============================================================
Transforms structured technical content into premium animated LinkedIn GIFs,
authentically matching the color usage, card gradients, and visual hierarchy of
Rushika Rai's LinkedIn reference posts (Types of APIs & Advanced Architectures).

Features:
- Exact Color Hierarchy from Reference Posts:
    * Two-tone title: Dark charcoal prefix + vibrant theme accent.
    * Dark solid rounded pill badges for column category headers with white text.
    * Top-to-bottom card gradients (white to soft pastel tint).
    * Pure white inner item cards with vector tech icon badges and bold typography.
    * Corner dot matrix decorations (like reference).
    * High-contrast connector lines with circular junction rings.
    * Radiant popping moving dots with dark contrast rings for 100% visibility.
- 3 Exact Themes:
    * 5: champagne_bronze   (Warm ivory, dark bronze pills, radiant fire amber flow)
    * 6: graphite_blue      (Ice blue canvas, dark navy pills, electric royal blue flow)
    * 4: royal_amethyst     (Lavender canvas, deep indigo pills, electric violet flow)
- Font Options:
    * --font modern (Inter/Helvetica/Arial display as in reference posts - default)
    * --font times  (Times New Roman)
- NO Core Takeaway banner generated.
- Pure animated GIF output only.
"""

import os
import re
import sys
import time
import math
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Union, Dict, Any
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. COLOR THEMES SAMPLED DIRECTLY FROM REFERENCE POSTS
# ==============================================================================
THEMES = {
    "champagne_bronze": {
        "id": "5",
        "name": "Champagne & Bronze",
        "bg": (255, 248, 236),              # #FFF8EC Warm champagne canvas
        "title_dark": (26, 26, 26),          # #1A1A1A
        "title_accent": (171, 77, 3),        # #AB4D03 Rich bronze accent
        "pill_dark": (132, 60, 10),          # #843C0A Dark chocolate bronze pill
        "card_grad_top": (255, 255, 255),    # White top
        "card_grad_bot": (245, 226, 204),    # Soft warm bronze gradient base
        "card_border": (214, 182, 145),      # Bronze card outline
        "item_card_bg": (255, 255, 255),     # Pure white inner cards
        "item_card_border": (232, 214, 190),
        "icon_badge_bg": (255, 245, 230),    # Soft ivory badge for icon
        "primary": (171, 77, 3),
        "text_dark": (35, 25, 18),
        "text_muted": (120, 105, 90),
        "connector_line": (90, 55, 30),      # Dark crisp connector lines
        "junction_dot": (171, 77, 3),
        "corner_dots": (215, 190, 160),
        # Moving Particle: Radiant Fire Amber + Dark Contrast Ring
        "particle_core": (255, 255, 255),
        "particle_glow": (234, 88, 12),      # Fire amber
        "particle_halo": (254, 215, 170),
        "particle_ring": (154, 52, 18),      # Dark contrast ring
        "hero_border": (171, 77, 3),
        "hero_tint": (255, 244, 230),
    },
    "graphite_blue": {
        "id": "6",
        "name": "Graphite & Electric Blue",
        "bg": (240, 244, 248),              # #F0F4F8 Clean ice blue canvas
        "title_dark": (26, 26, 26),          # #1A1A1A
        "title_accent": (1, 85, 210),        # #0155D2 Electric royal blue accent
        "pill_dark": (39, 60, 86),           # #273C56 Dark slate navy pill
        "card_grad_top": (255, 255, 255),    # White top
        "card_grad_bot": (205, 225, 248),    # Soft ice blue gradient base
        "card_border": (150, 185, 220),      # Blue card outline
        "item_card_bg": (255, 255, 255),     # Pure white inner cards
        "item_card_border": (210, 225, 242),
        "icon_badge_bg": (240, 247, 255),    # Soft blue badge for icon
        "primary": (1, 85, 210),
        "text_dark": (20, 26, 36),
        "text_muted": (90, 105, 125),
        "connector_line": (35, 55, 80),      # Dark crisp connector lines
        "junction_dot": (1, 85, 210),
        "corner_dots": (185, 205, 225),
        # Moving Particle: Electric Royal Blue + Midnight Contrast Ring
        "particle_core": (255, 255, 255),
        "particle_glow": (0, 102, 255),      # Radiant electric blue
        "particle_halo": (147, 197, 253),
        "particle_ring": (20, 45, 95),       # Midnight contrast ring
        "hero_border": (1, 85, 210),
        "hero_tint": (235, 245, 255),
    },
    "royal_amethyst": {
        "id": "4",
        "name": "Royal Amethyst",
        "bg": (250, 245, 255),              # #FAF5FF Soft royal lavender canvas
        "title_dark": (26, 26, 26),          # #1A1A1A
        "title_accent": (94, 39, 193),       # #5E27C1 Rich royal violet accent
        "pill_dark": (67, 28, 130),          # #431C82 Deep royal violet pill
        "card_grad_top": (255, 255, 255),    # White top
        "card_grad_bot": (222, 210, 250),    # Soft lavender gradient base
        "card_border": (175, 155, 225),      # Amethyst card outline
        "item_card_bg": (255, 255, 255),     # Pure white inner cards
        "item_card_border": (225, 215, 245),
        "icon_badge_bg": (245, 240, 255),    # Soft lavender badge for icon
        "primary": (94, 39, 193),
        "text_dark": (35, 20, 50),
        "text_muted": (110, 95, 130),
        "connector_line": (60, 30, 100),     # Dark crisp connector lines
        "junction_dot": (94, 39, 193),
        "corner_dots": (205, 190, 230),
        # Moving Particle: Radiant Vivid Violet + Deep Violet Contrast Ring
        "particle_core": (255, 255, 255),
        "particle_glow": (147, 51, 234),     # Electric violet
        "particle_halo": (216, 180, 254),
        "particle_ring": (76, 29, 149),      # Deep contrast ring
        "hero_border": (94, 39, 193),
        "hero_tint": (248, 242, 255),
    }
}

THEME_ALIASES = {
    "4": "royal_amethyst",
    "amethyst": "royal_amethyst",
    "royal": "royal_amethyst",
    "royal_amethyst": "royal_amethyst",
    "5": "champagne_bronze",
    "bronze": "champagne_bronze",
    "champagne": "champagne_bronze",
    "champagne_bronze": "champagne_bronze",
    "6": "graphite_blue",
    "blue": "graphite_blue",
    "electric_blue": "graphite_blue",
    "graphite": "graphite_blue",
    "graphite_blue": "graphite_blue",
}

SIZE_PRESETS = {
    "landscape": (1200, 630),
    "portrait": (1080, 1350),
    "square": (1080, 1080),
    "poster": (1400, 800),
}

# ==============================================================================
# 2. TYPOGRAPHY ENGINE (MODERN DISPLAY & TIMES NEW ROMAN)
# ==============================================================================
def get_font_instance(font_family, size, bold=False):
    # Check bundled high-resolution font assets first (ensures cross-platform Docker/Render parity)
    base_dir = Path(__file__).resolve().parent.parent
    bundled_bold = base_dir / "assets" / "fonts" / "Arial-Bold.ttf"
    bundled_reg = base_dir / "assets" / "fonts" / "Arial.ttf"

    if font_family != "times":
        if bold and bundled_bold.exists():
            try:
                return ImageFont.truetype(str(bundled_bold), int(size))
            except Exception:
                pass
        elif not bold and bundled_reg.exists():
            try:
                return ImageFont.truetype(str(bundled_reg), int(size))
            except Exception:
                pass

    if font_family == "times":
        candidates_bold = [
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
            "/Library/Fonts/Times New Roman Bold.ttf",
            "/System/Library/Fonts/Times.ttc"
        ]
        candidates_reg = [
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/Library/Fonts/Times New Roman.ttf",
            "/System/Library/Fonts/Times.ttc"
        ]
    else:
        # Modern display (Helvetica / SF Compact / Arial as in reference posts)
        candidates_bold = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"
        ]
        candidates_reg = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFCompact.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"
        ]

    candidates = candidates_bold if bold else candidates_reg
    for path in candidates:
        if os.path.exists(path):
            try:
                index = 1 if bold and ("Helvetica.ttc" in path or "Times.ttc" in path) else 0
                return ImageFont.truetype(path, int(size), index=index)
            except Exception:
                continue
    return ImageFont.load_default()


# ==============================================================================
# 3. VECTOR TECH ICONS (ZERO EMOJIS)
# ==============================================================================
def draw_vector_icon(draw, icon_name, cx, cy, size=22, color=(109, 69, 197)):
    s = size
    lw = max(1.5, s * 0.09)

    if icon_name == "document":
        w, h = s * 0.72, s * 0.95
        x0, y0 = cx - w/2, cy - h/2
        fold = s * 0.26
        pts = [(x0, y0), (x0 + w - fold, y0), (x0 + w, y0 + fold), (x0 + w, y0 + h), (x0, y0 + h)]
        draw.polygon(pts, fill=None, outline=color)
        draw.line([(x0 + w - fold, y0), (x0 + w - fold, y0 + fold), (x0 + w, y0 + fold)], fill=color, width=int(lw))
        draw.line([(x0 + s*0.14, y0 + s*0.42), (x0 + w - s*0.14, y0 + s*0.42)], fill=color, width=int(lw))
        draw.line([(x0 + s*0.14, y0 + s*0.62), (x0 + w - s*0.14, y0 + s*0.62)], fill=color, width=int(lw))

    elif icon_name == "database":
        w = s * 0.82
        h_d = s * 0.26
        x0, x1 = cx - w/2, cx + w/2
        for i in range(3):
            y_disk = cy - s*0.32 + i * (s * 0.32)
            draw.ellipse([x0, y_disk - h_d/2, x1, y_disk + h_d/2], outline=color, width=int(lw))
            if i < 2:
                draw.line([(x0, y_disk), (x0, y_disk + s*0.32)], fill=color, width=int(lw))
                draw.line([(x1, y_disk), (x1, y_disk + s*0.32)], fill=color, width=int(lw))

    elif icon_name == "graph":
        r = s * 0.13
        p_top = (cx, cy - s*0.34)
        p_left = (cx - s*0.33, cy + s*0.12)
        p_right = (cx + s*0.33, cy + s*0.12)
        p_bot = (cx, cy + s*0.36)
        draw.line([p_top, p_left], fill=color, width=int(lw))
        draw.line([p_top, p_right], fill=color, width=int(lw))
        draw.line([p_left, p_bot], fill=color, width=int(lw))
        draw.line([p_right, p_bot], fill=color, width=int(lw))
        draw.line([p_left, p_right], fill=color, width=max(1, int(lw*0.8)))
        for p in [p_top, p_left, p_right, p_bot]:
            draw.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=(255, 255, 255), outline=color, width=int(lw))

    elif icon_name == "search":
        r = s * 0.3
        c_x, c_y = cx - s*0.08, cy - s*0.08
        draw.ellipse([c_x - r, c_y - r, c_x + r, c_y + r], outline=color, width=int(lw))
        hx0 = c_x + r * 0.707
        hy0 = c_y + r * 0.707
        hx1 = hx0 + s * 0.32
        hy1 = hy0 + s * 0.32
        draw.line([(hx0, hy0), (hx1, hy1)], fill=color, width=int(lw*1.5))

    elif icon_name == "brain":
        r = s * 0.36
        draw.arc([cx - r, cy - r, cx, cy + r], 90, 270, fill=color, width=int(lw))
        draw.arc([cx, cy - r, cx + r, cy + r], 270, 90, fill=color, width=int(lw))
        draw.line([(cx, cy - r + 2), (cx, cy + r - 2)], fill=color, width=int(lw))
        for dx, dy in [(-r*0.5, -r*0.3), (-r*0.5, r*0.3), (r*0.5, -r*0.3), (r*0.5, r*0.3), (0, 0)]:
            draw.ellipse([cx+dx-1.5, cy+dy-1.5, cx+dx+1.5, cy+dy+1.5], fill=color)

    elif icon_name == "chart":
        w_b = s * 0.18
        base_y = cy + s * 0.38
        bars = [0.35, 0.72, 0.52]
        for i, h in enumerate(bars):
            bx = cx - s * 0.35 + i * (w_b + s*0.1)
            draw.rectangle([bx, base_y - s * h, bx + w_b, base_y], outline=color, width=int(lw))
        draw.line([(cx - s * 0.42, base_y), (cx + s * 0.42, base_y)], fill=color, width=int(lw))

    elif icon_name == "shield":
        w, h = s * 0.7, s * 0.85
        x0, y0 = cx - w/2, cy - h/2
        pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h*0.55), (cx, y0 + h), (x0, y0 + h*0.55)]
        draw.polygon(pts, fill=None, outline=color)
        draw.line([(cx - s*0.14, cy), (cx - s*0.02, cy + s*0.12)], fill=color, width=int(lw))
        draw.line([(cx - s*0.02, cy + s*0.12), (cx + s*0.18, cy - s*0.1)], fill=color, width=int(lw))

    elif icon_name == "clock":
        r = s * 0.38
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(lw))
        draw.line([(cx, cy), (cx, cy - r*0.65)], fill=color, width=int(lw))
        draw.line([(cx, cy), (cx + r*0.5, cy)], fill=color, width=int(lw))

    else:
        r = s * 0.35
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(lw))
        draw.ellipse([cx - r*0.45, cy - r*0.45, cx + r*0.45, cy + r*0.45], outline=color, width=int(lw))

def pick_icon_for_item(text):
    t = text.lower()
    if any(k in t for k in ["parse", "chunk", "document", "cleaning", "text", "invoices"]):
        return "document"
    if any(k in t for k in ["vector", "embed", "index", "storage", "database", "ann", "s3", "tokens"]):
        return "database"
    if any(k in t for k in ["graph", "entity", "relation", "community", "cluster", "traverse", "multi-hop", "network"]):
        return "graph"
    if any(k in t for k in ["search", "bm25", "keyword", "retrieval", "query", "hybrid", "rerank"]):
        return "search"
    if any(k in t for k in ["reason", "llm", "synthesis", "answer", "generation", "prompt", "model", "cortex"]):
        return "brain"
    if any(k in t for k in ["ground", "citation", "validation", "faithful", "guardrail", "schema"]):
        return "shield"
    if any(k in t for k in ["metric", "accuracy", "latency", "benchmark", "quality", "eval", "observability", "log"]):
        return "chart"
    if any(k in t for k in ["freshness", "re-index", "feedback", "loop", "clock", "sla", "alert"]):
        return "clock"
    return "database"

def split_item_text(text):
    m = re.match(r"^(.*?)\s*(\(.*?\))\s*$", text.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m2 = re.match(r"^(.*?)\s*[-—:]\s*(.*?)$", text.strip())
    if m2 and len(m2.group(1)) < 30:
        return m2.group(1).strip(), m2.group(2).strip()
    return text.strip(), ""

# ==============================================================================
# 4. CONTENT PARSER (NO TAKEAWAY)
# ==============================================================================
def parse_content_input(raw_input):
    if os.path.exists(raw_input) and os.path.isfile(raw_input):
        with open(raw_input, "r", encoding="utf-8") as f:
            content_str = f.read()
    else:
        content_str = raw_input

    trimmed = content_str.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
        try:
            data = json.loads(trimmed)
            data.pop("takeaway", None)
            return data
        except json.JSONDecodeError:
            pass

    data = {"layers": []}
    lines = content_str.strip().split("\n")
    current_layer = None
    in_comparison = False
    current_comp_side = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if "takeaway" in line.lower():
            continue

        if line.lower().startswith("title:"):
            data["title"] = line.split(":", 1)[1].strip().strip("*").strip()
            continue

        if line.lower().startswith("subtitle:"):
            data["subtitle"] = line.split(":", 1)[1].strip().strip("*").strip()
            continue

        if "comparison:" in line.lower() or ("vs" in line.lower() and ("bottom" in line.lower() or "compare" in line.lower())):
            in_comparison = True
            data["comparison"] = {"left": {"bullets": []}, "right": {"bullets": []}}
            continue

        if in_comparison:
            if not line.startswith("-") and not line.startswith("•") and not line.startswith("*"):
                clean_name = line.strip().strip("*").strip("#").strip()
                if not data["comparison"]["left"].get("title"):
                    data["comparison"]["left"]["title"] = clean_name
                    current_comp_side = "left"
                elif not data["comparison"]["right"].get("title"):
                    data["comparison"]["right"]["title"] = clean_name
                    current_comp_side = "right"
                continue
            else:
                item_text = line.lstrip("-•* ").strip()
                if current_comp_side:
                    data["comparison"][current_comp_side]["bullets"].append(item_text)
                continue

        layer_match = re.match(r"(?:Layer\s*(\d+)|Step\s*(\d+))\s*[-—:]\s*(.*?)(?:\((.*?)\))?$", line, re.IGNORECASE)
        if layer_match:
            num = layer_match.group(1) or layer_match.group(2) or str(len(data["layers"]) + 1)
            name = layer_match.group(3).strip().strip("*").strip()
            desc = (layer_match.group(4) or "").strip()
            current_layer = {
                "name": name,
                "desc": desc,
                "badge": num,
                "items": []
            }
            data["layers"].append(current_layer)
            continue

        if line.startswith("-") or line.startswith("•") or line.startswith("*"):
            item_text = line.lstrip("-•* ").strip()
            if current_layer:
                current_layer["items"].append(item_text)

    return data

def resolve_canvas_size(requested_size, content):
    if requested_size in SIZE_PRESETS:
        return SIZE_PRESETS[requested_size]

    if "x" in requested_size:
        parts = requested_size.lower().split("x")
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            pass

    layers = content.get("layers", [])
    layer_count = len(layers)
    has_comparison = "comparison" in content and bool(content["comparison"])

    if layer_count >= 5 and has_comparison:
        return SIZE_PRESETS["poster"]     # 1400x800 for best spacing
    elif layer_count >= 5:
        return SIZE_PRESETS["landscape"]
    elif layer_count <= 3:
        return SIZE_PRESETS["square"]
    else:
        return SIZE_PRESETS["poster"]

# ==============================================================================
# 5. DIAGRAM LAYOUT RENDERER (AUTHENTIC REFERENCE STYLING)
# ==============================================================================
def draw_gradient_card(draw, box, top_color, bot_color, radius=10, outline=None, width=1):
    """Renders a smooth vertical gradient rounded card container."""
    x0, y0, x1, y1 = box
    h = y1 - y0
    for y in range(y0, y1):
        frac = (y - y0) / max(1, h)
        r = int(top_color[0] * (1 - frac) + bot_color[0] * frac)
        g = int(top_color[1] * (1 - frac) + bot_color[1] * frac)
        b = int(top_color[2] * (1 - frac) + bot_color[2] * frac)
        draw.line([(x0, y), (x1, y)], fill=(r, g, b))
    if outline:
        draw.rounded_rectangle(box, radius=radius, outline=outline, width=width)

def render_base_diagram(width, height, content, theme_key, font_family="modern"):
    theme = THEMES[theme_key]
    img = Image.new("RGBA", (width, height), theme["bg"])
    draw = ImageDraw.Draw(img)

    scale_x = width / 1400.0
    scale_y = height / 800.0
    scale = min(scale_x, scale_y)

    # 1. Corner Decorative Dot Matrices (4 rows x 5 columns) matching reference posts
    c_dots = theme["corner_dots"]
    for r in range(4):
        for c in range(5):
            # Top-Right corner
            draw.ellipse([width - int(70*scale_x) + c*int(11*scale), int(18*scale_y) + r*int(11*scale),
                          width - int(70*scale_x) + c*int(11*scale) + int(3.5*scale), int(18*scale_y) + r*int(11*scale) + int(3.5*scale)], fill=c_dots)
            # Bottom-Left corner
            draw.ellipse([int(20*scale_x) + c*int(11*scale), height - int(55*scale_y) + r*int(11*scale),
                          int(20*scale_x) + c*int(11*scale) + int(3.5*scale), height - int(55*scale_y) + r*int(11*scale) + int(3.5*scale)], fill=c_dots)

    # Typography Sizes
    title_size = max(24, int(36 * scale))
    sub_size = max(12, int(15.5 * scale))
    pill_font_size = max(11, int(14.5 * scale))
    item_title_size = max(11.5, int(14.5 * scale))
    item_sub_size = max(9.5, int(11.5 * scale))
    comp_title_size = max(13.5, int(17.5 * scale))
    comp_bullet_size = max(11, int(13.5 * scale))

    f_title = get_font_instance(font_family, title_size, bold=True)
    f_sub = get_font_instance(font_family, sub_size, bold=False)
    f_pill = get_font_instance(font_family, pill_font_size, bold=True)
    f_item_title = get_font_instance(font_family, item_title_size, bold=True)
    f_item_sub = get_font_instance(font_family, item_sub_size, bold=False)
    f_comp_title = get_font_instance(font_family, comp_title_size, bold=True)
    f_comp_bullet = get_font_instance(font_family, comp_bullet_size, bold=False)

    # 2. Two-Tone Title Header (e.g. "Types of " in dark + "APIs & Their Use Cases" in theme accent)
    raw_title = content.get("title", "Advanced RAG & Retrieval Architectures")
    # Split into dark prefix and colored accent
    if ":" in raw_title:
        title_p1, title_p2 = raw_title.split(":", 1)
        title_p1 = title_p1.strip() + ": "
        title_p2 = title_p2.strip()
    elif "&" in raw_title:
        parts = raw_title.split("&", 1)
        title_p1 = parts[0].strip() + " & "
        title_p2 = parts[1].strip()
    else:
        words = raw_title.split()
        mid = len(words) // 2
        title_p1 = " ".join(words[:mid]) + " "
        title_p2 = " ".join(words[mid:])

    bb1 = draw.textbbox((0, 0), title_p1, font=f_title)
    bb2 = draw.textbbox((0, 0), title_p2, font=f_title)
    w1 = bb1[2] - bb1[0]
    w2 = bb2[2] - bb2[0]
    total_title_w = w1 + w2
    title_x0 = (width - total_title_w) // 2
    title_y = int(18 * scale_y)

    draw.text((title_x0, title_y), title_p1, fill=theme["title_dark"], font=f_title)
    draw.text((title_x0 + w1, title_y), title_p2, fill=theme["title_accent"], font=f_title)

    # Subtitle pill
    subtitle = content.get("subtitle", "")
    current_y = title_y + (bb1[3] - bb1[1]) + int(6 * scale_y)
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=f_sub)
        sub_w = sub_bbox[2] - sub_bbox[0]
        sub_h = sub_bbox[3] - sub_bbox[1]
        pill_pad_x = int(16 * scale_x)
        pill_pad_y = int(4 * scale_y)
        pill_box = [
            (width - sub_w) // 2 - pill_pad_x,
            current_y,
            (width + sub_w) // 2 + pill_pad_x,
            current_y + sub_h + pill_pad_y * 2
        ]
        draw.rounded_rectangle(pill_box, radius=int(10 * scale), fill=theme["card_grad_bot"], outline=theme["card_border"], width=1)
        draw.text(((width - sub_w) // 2, current_y + pill_pad_y), subtitle, fill=theme["title_accent"], font=f_sub)
        current_y = pill_box[3] + int(14 * scale_y)
    else:
        current_y += int(10 * scale_y)

    # 3. Vertical Space Budgeting
    layers = content.get("layers", [])
    num_layers = max(1, len(layers))
    has_comparison = "comparison" in content and bool(content["comparison"])

    margin_x = int(22 * scale_x)
    bottom_margin = int(18 * scale_y)
    comp_h = int(165 * scale_y) if has_comparison else 0
    feedback_bus_h = int(26 * scale_y)

    header_pill_h = int(32 * scale_y)
    layer_top_y = current_y + header_pill_h + int(8 * scale_y)
    layer_bottom_y = height - bottom_margin - (comp_h + feedback_bus_h if has_comparison else feedback_bus_h)
    layer_total_h = layer_bottom_y - layer_top_y

    gutter = int(14 * scale_x)
    total_gutters = (num_layers - 1) * gutter
    col_width = (width - 2 * margin_x - total_gutters) / num_layers

    paths = []
    layer_cards_info = []

    # 4. Render Each Layer Column with Dark Header Pill & Gradient Container
    for i, layer in enumerate(layers):
        col_x0 = int(margin_x + i * (col_width + gutter))
        col_x1 = int(col_x0 + col_width)

        is_hero = layer.get("hero", False) or (num_layers >= 5 and i == 2)

        # A. Dark Solid Pill Header at Top of Column (Exactly like reference)
        pill_box = [col_x0, current_y, col_x1, current_y + header_pill_h]
        draw.rounded_rectangle(pill_box, radius=int(8 * scale), fill=theme["pill_dark"])

        layer_name = layer.get("name", f"Layer {i+1}")
        badge_text = str(layer.get("badge", i + 1))
        header_title = f"{badge_text}. {layer_name}"
        hb_bb = draw.textbbox((0, 0), header_title, font=f_pill)
        hb_w = hb_bb[2] - hb_bb[0]
        hb_h = hb_bb[3] - hb_bb[1]
        draw.text(((col_x0 + col_x1 - hb_w) // 2, current_y + (header_pill_h - hb_h) // 2 - 1),
                  header_title, fill=(255, 255, 255), font=f_pill)

        # B. Gradient Card Container
        border_col = theme["hero_border"] if is_hero else theme["card_border"]
        border_w = 2 if is_hero else 1
        card_box = [col_x0, layer_top_y, col_x1, layer_bottom_y]
        draw_gradient_card(draw, card_box, theme["card_grad_top"], theme["card_grad_bot"],
                           radius=int(10 * scale), outline=border_col, width=border_w)

        # C. Inner Item Cards (Pure White rounded cards like reference)
        items = layer.get("items", [])
        num_items = len(items)

        pad_in = int(10 * scale)
        substrate_h = int(28 * scale_y)
        item_area_top = layer_top_y + pad_in
        item_area_bottom = layer_bottom_y - pad_in - substrate_h - int(6 * scale_y)
        item_area_h = item_area_bottom - item_area_top

        item_h = max(34, int(item_area_h / max(1, num_items) - int(6 * scale_y)))
        item_gap = int((item_area_h - num_items * item_h) / max(1, num_items - 1)) if num_items > 1 else 0

        spine_x = col_x0 + int(14 * scale_x)
        item_box_x0 = col_x0 + int(24 * scale_x)
        item_box_x1 = col_x1 - pad_in

        item_pins = []
        for j, it in enumerate(items):
            iy0 = item_area_top + j * (item_h + item_gap)
            iy1 = iy0 + item_h
            icy = (iy0 + iy1) // 2

            # Pure white card background with subtle outline
            draw.rounded_rectangle(
                [item_box_x0, iy0, item_box_x1, iy1],
                radius=int(6 * scale),
                fill=theme["item_card_bg"],
                outline=theme["item_card_border"],
                width=1
            )

            it_raw = it if isinstance(it, str) else it.get("title", "")
            it_title, it_sub = split_item_text(it_raw)

            # Icon Box with Soft Tint Background
            icon_name = pick_icon_for_item(it_raw)
            icon_box_size = max(20, int(item_h * 0.62))
            icon_cx = item_box_x0 + int(14 * scale_x)
            icon_cy = icy

            draw.rounded_rectangle(
                [icon_cx - icon_box_size//2, icon_cy - icon_box_size//2, icon_cx + icon_box_size//2, icon_cy + icon_box_size//2],
                radius=int(4 * scale),
                fill=theme["icon_badge_bg"],
                outline=theme["item_card_border"],
                width=1
            )
            draw_vector_icon(draw, icon_name, icon_cx, icon_cy, size=int(icon_box_size * 0.85), color=theme["primary"])

            # Text Placement with auto-fit to avoid edge overflow
            text_x = icon_cx + icon_box_size//2 + int(8 * scale_x)
            max_text_w = item_box_x1 - text_x - int(5 * scale_x)

            curr_f_title = f_item_title
            tb = draw.textbbox((0, 0), it_title, font=curr_f_title)
            if (tb[2] - tb[0]) > max_text_w:
                curr_f_title = get_font_instance(font_family, max(10, int(item_title_size * 0.9)), bold=True)

            if it_sub:
                draw.text((text_x, icy - int(10 * scale_y)), it_title, fill=theme["text_dark"], font=curr_f_title)
                draw.text((text_x, icy + int(4 * scale_y)), it_sub, fill=theme["text_muted"], font=f_item_sub)
            else:
                tb_m = draw.textbbox((0, 0), it_title, font=curr_f_title)
                th_m = tb_m[3] - tb_m[1]
                draw.text((text_x, icy - th_m // 2 - 1), it_title, fill=theme["text_dark"], font=curr_f_title)

            pin_pos = (spine_x, icy)
            item_pins.append(pin_pos)

            draw.line([(spine_x, icy), (item_box_x0, icy)], fill=theme["connector_line"], width=int(1.5 * scale))
            draw.ellipse([spine_x - 2, icy - 2, spine_x + 2, icy + 2], fill=theme["junction_dot"])

        # Intra-layer vertical spine
        if len(item_pins) > 1:
            draw.line([item_pins[0], item_pins[-1]], fill=theme["connector_line"], width=int(2 * scale))
            for k in range(len(item_pins) - 1):
                paths.append({
                    "type": "spine",
                    "pts": [item_pins[k], item_pins[k+1]],
                    "period": 2.0,
                    "color": theme["particle_glow"]
                })

        # Substrate Pill at bottom of card
        substrate_text = layer.get("substrate", "")
        if substrate_text:
            sub_y0 = layer_bottom_y - pad_in - substrate_h
            draw.rounded_rectangle(
                [col_x0 + pad_in, sub_y0, col_x1 - pad_in, sub_y0 + substrate_h],
                radius=int(6 * scale),
                fill=theme["item_card_bg"],
                outline=theme["card_border"],
                width=1
            )
            st_bb = draw.textbbox((0, 0), substrate_text, font=f_pill)
            draw.text(
                ((col_x0 + col_x1 - (st_bb[2] - st_bb[0])) // 2, sub_y0 + (substrate_h - (st_bb[3] - st_bb[1])) // 2 - 1),
                substrate_text,
                fill=theme["primary"],
                font=f_pill
            )

        layer_cards_info.append({
            "col_x0": col_x0,
            "col_x1": col_x1,
            "top_y": layer_top_y,
            "bottom_y": layer_bottom_y,
            "pins": item_pins,
            "is_hero": is_hero
        })

    # 5. Inter-Layer Horizontal Bridges
    for i in range(num_layers - 1):
        l1 = layer_cards_info[i]
        l2 = layer_cards_info[i+1]

        p_from_y = l1["pins"][min(2, len(l1["pins"])-1)][1] if l1["pins"] else (l1["top_y"] + l1["bottom_y"]) // 2
        p_to_y = l2["pins"][min(1, len(l2["pins"])-1)][1] if l2["pins"] else (l2["top_y"] + l2["bottom_y"]) // 2

        x_out = l1["col_x1"]
        x_in = l2["col_x0"]

        if abs(p_from_y - p_to_y) < 5:
            draw.line([(x_out, p_from_y), (x_in, p_from_y)], fill=theme["connector_line"], width=int(2 * scale))
            draw.ellipse([x_out - 3, p_from_y - 3, x_out + 3, p_from_y + 3], outline=theme["connector_line"], fill=(255, 255, 255), width=2)
            draw.ellipse([x_in - 3, p_from_y - 3, x_in + 3, p_from_y + 3], outline=theme["connector_line"], fill=(255, 255, 255), width=2)
            paths.append({
                "type": "bridge",
                "pts": [(x_out, p_from_y), (x_in, p_from_y)],
                "period": 2.0,
                "color": theme["particle_glow"]
            })
        else:
            mid_x = (x_out + x_in) // 2
            bridge_pts = [(x_out, p_from_y), (mid_x, p_from_y), (mid_x, p_to_y), (x_in, p_to_y)]
            for s in range(len(bridge_pts) - 1):
                draw.line([bridge_pts[s], bridge_pts[s+1]], fill=theme["connector_line"], width=int(2 * scale))
            draw.ellipse([x_out - 3, p_from_y - 3, x_out + 3, p_from_y + 3], outline=theme["connector_line"], fill=(255, 255, 255), width=2)
            draw.ellipse([x_in - 3, p_to_y - 3, x_in + 3, p_to_y + 3], outline=theme["connector_line"], fill=(255, 255, 255), width=2)
            paths.append({
                "type": "bridge",
                "pts": bridge_pts,
                "period": 2.5,
                "color": theme["particle_glow"]
            })

    # 6. Hero 3-Way Parallel Branch & Convergence (Layer 3)
    if num_layers >= 5:
        l3 = layer_cards_info[2]
        if len(l3["pins"]) >= 4:
            rx = l3["col_x1"] - int(10 * scale_x)
            p_dense = (rx, l3["pins"][0][1])
            p_sparse = (rx, l3["pins"][1][1])
            p_graph = (rx, l3["pins"][2][1])
            p_rerank = (rx, l3["pins"][3][1])

            draw.line([p_dense, (rx, p_rerank[1])], fill=theme["connector_line"], width=int(1.5 * scale))
            for pt in [p_dense, p_sparse, p_graph, p_rerank]:
                draw.ellipse([pt[0]-2, pt[1]-2, pt[0]+2, pt[1]+2], fill=theme["junction_dot"])

            paths.append({
                "type": "branch",
                "pts": [p_dense, (rx, p_rerank[1])],
                "period": 2.0,
                "color": theme["particle_glow"]
            })

    # 7. Reverse Feedback Telemetry Bus
    bus_y = layer_bottom_y + int(14 * scale_y)
    bus_x_start = layer_cards_info[-1]["col_x1"]
    bus_x_end = layer_cards_info[0]["col_x0"]

    l_last = layer_cards_info[-1]
    last_pin_y = l_last["pins"][-1][1] if l_last["pins"] else l_last["bottom_y"] - 20

    draw.line([(l_last["col_x1"], last_pin_y), (l_last["col_x1"] + 6, last_pin_y), (l_last["col_x1"] + 6, bus_y), (bus_x_end, bus_y)], fill=theme["connector_line"], width=int(1.5 * scale))
    draw.ellipse([bus_x_end - 2, bus_y - 2, bus_x_end + 2, bus_y + 2], fill=theme["junction_dot"])

    bus_label = "<-- CONTINUOUS FEEDBACK, CACHE INVALIDATION & GRAPH RE-INDEXING BUS <--"
    f_bus = get_font_instance(font_family, max(9, int(11 * scale)), bold=True)
    b_bb = draw.textbbox((0, 0), bus_label, font=f_bus)
    b_w = b_bb[2] - b_bb[0]
    draw.text(((width - b_w) // 2, bus_y - int(11 * scale_y)), bus_label, fill=theme["text_muted"], font=f_bus)

    paths.append({
        "type": "bus",
        "pts": [(l_last["col_x1"] + 6, bus_y), (bus_x_end, bus_y)],
        "period": 4.0,
        "color": theme["particle_glow"]
    })

    # 8. Bottom Comparison Cards (Matching Reference Sub-card Aesthetics)
    comp = content.get("comparison")
    if comp:
        comp_y0 = bus_y + int(14 * scale_y)
        comp_y1 = comp_y0 + comp_h - int(10 * scale_y)
        comp_w = (width - 2 * margin_x - gutter) // 2

        # Left Card (Dense Vector Search)
        left_info = comp.get("left", {})
        left_title = left_info.get("title", "Dense Vector Search")
        left_box = [margin_x, comp_y0, margin_x + comp_w, comp_y1]
        draw_gradient_card(draw, left_box, (255, 255, 255), theme["card_grad_bot"],
                           radius=int(8 * scale), outline=theme["card_border"], width=1)

        draw_vector_icon(draw, "database", margin_x + 20, comp_y0 + 20, size=int(16 * scale), color=theme["primary"])
        draw.text((margin_x + 36, comp_y0 + 12), left_title, fill=theme["text_dark"], font=f_comp_title)

        pipe_steps = left_info.get("pipeline", ["Query", "Dense Embed", "ANN Index", "Top-K Chunks"])
        pw = (comp_w - 30) // len(pipe_steps)
        for s_idx, step_name in enumerate(pipe_steps):
            px0 = margin_x + 15 + s_idx * pw
            px1 = px0 + pw - 6
            py0 = comp_y0 + int(36 * scale_y)
            py1 = py0 + int(22 * scale_y)
            draw.rounded_rectangle([px0, py0, px1, py1], radius=int(4 * scale), fill=theme["item_card_bg"], outline=theme["item_card_border"], width=1)
            sb = draw.textbbox((0, 0), step_name, font=f_comp_bullet)
            draw.text(((px0 + px1 - (sb[2] - sb[0])) // 2, py0 + int(2 * scale_y)), step_name, fill=theme["text_dark"], font=f_comp_bullet)
            if s_idx < len(pipe_steps) - 1:
                draw.text((px1 + 1, py0 + int(2 * scale_y)), "→", fill=theme["connector_line"], font=f_comp_bullet)

        bullets = left_info.get("bullets", [
            "Semantic similarity matching across dense embedding space",
            "Strong for focused, factoid and local passage questions",
            "Fast, horizontally scalable retrieval (sub-50ms latency)",
            "Limited explicit relationship and multi-hop traversal"
        ])
        for b_idx, bullet in enumerate(bullets[:4]):
            by = comp_y0 + int(66 * scale_y) + b_idx * int(17 * scale_y)
            draw_vector_icon(draw, "target", margin_x + 22, by + 7, size=int(11 * scale), color=theme["primary"])
            draw.text((margin_x + 34, by), bullet, fill=theme["text_dark"], font=f_comp_bullet)

        # Right Card (GraphRAG)
        right_info = comp.get("right", {})
        right_title = right_info.get("title", "GraphRAG (Knowledge Graph Augmented)")
        right_x0 = margin_x + comp_w + gutter
        right_box = [right_x0, comp_y0, right_x0 + comp_w, comp_y1]
        draw_gradient_card(draw, right_box, (255, 255, 255), theme["card_grad_bot"],
                           radius=int(8 * scale), outline=theme["card_border"], width=1)

        draw_vector_icon(draw, "graph", right_x0 + 20, comp_y0 + 20, size=int(16 * scale), color=theme["primary"])
        draw.text((right_x0 + 36, comp_y0 + 12), right_title, fill=theme["text_dark"], font=f_comp_title)

        pipe_steps_r = right_info.get("pipeline", ["Query", "Entity Extr", "Graph Walk", "Communities", "Fused Context"])
        pw_r = (comp_w - 30) // len(pipe_steps_r)
        for s_idx, step_name in enumerate(pipe_steps_r):
            px0 = right_x0 + 15 + s_idx * pw_r
            px1 = px0 + pw_r - 6
            py0 = comp_y0 + int(36 * scale_y)
            py1 = py0 + int(22 * scale_y)
            draw.rounded_rectangle([px0, py0, px1, py1], radius=int(4 * scale), fill=theme["item_card_bg"], outline=theme["item_card_border"], width=1)
            sb = draw.textbbox((0, 0), step_name, font=f_comp_bullet)
            draw.text(((px0 + px1 - (sb[2] - sb[0])) // 2, py0 + int(2 * scale_y)), step_name, fill=theme["text_dark"], font=f_comp_bullet)
            if s_idx < len(pipe_steps_r) - 1:
                draw.text((px1 + 1, py0 + int(2 * scale_y)), "→", fill=theme["connector_line"], font=f_comp_bullet)

        bullets_r = right_info.get("bullets", [
            "Entity and relationship-aware multi-hop graph retrieval",
            "Deep reasoning across interconnected, non-contiguous facts",
            "Precomputed community summaries for global / thematic questions",
            "Higher construction complexity; combined with dense vectors for hybrid"
        ])
        for b_idx, bullet in enumerate(bullets_r[:4]):
            by = comp_y0 + int(66 * scale_y) + b_idx * int(17 * scale_y)
            draw_vector_icon(draw, "shield", right_x0 + 22, by + 7, size=int(11 * scale), color=theme["primary"])
            draw.text((right_x0 + 34, by), bullet, fill=theme["text_dark"], font=f_comp_bullet)

        # VS Badge
        vs_cx = margin_x + comp_w + gutter // 2
        vs_cy = (comp_y0 + comp_y1) // 2
        vs_r = int(15 * scale)
        draw.ellipse([vs_cx - vs_r, vs_cy - vs_r, vs_cx + vs_r, vs_cy + vs_r], fill=theme["pill_dark"])
        vs_bb = draw.textbbox((0, 0), "VS", font=f_comp_bullet)
        draw.text((vs_cx - (vs_bb[2] - vs_bb[0]) // 2, vs_cy - (vs_bb[3] - vs_bb[1]) // 2 - 1), "VS", fill=(255, 255, 255), font=f_comp_bullet)

    return img, paths

# ==============================================================================
# 6. SIMULTANEOUS FLOW WITH HIGH-CONTRAST PARTICLES
# ==============================================================================
def interpolate_path(pts, t):
    if not pts:
        return (0, 0)
    if len(pts) == 1:
        return pts[0]

    lengths = []
    total_len = 0.0
    for i in range(len(pts) - 1):
        dx = pts[i+1][0] - pts[i][0]
        dy = pts[i+1][1] - pts[i][1]
        seg_len = math.hypot(dx, dy)
        lengths.append(seg_len)
        total_len += seg_len

    if total_len == 0.0:
        return pts[0]

    target_d = (t % 1.0) * total_len
    cum_d = 0.0
    for i, seg_len in enumerate(lengths):
        if cum_d + seg_len >= target_d:
            remain = target_d - cum_d
            frac = remain / seg_len if seg_len > 0 else 0
            x = pts[i][0] + frac * (pts[i+1][0] - pts[i][0])
            y = pts[i][1] + frac * (pts[i+1][1] - pts[i][1])
            return (int(x), int(y))
        cum_d += seg_len

    return pts[-1]

def draw_popping_particle(draw, pos, theme, r_glow=7, r_core=3):
    cx, cy = pos
    # 1. Outer halo
    draw.ellipse([cx - r_glow, cy - r_glow, cx + r_glow, cy + r_glow], fill=theme["particle_halo"])
    # 2. Dark contrast outline ring
    r_ring = r_glow - 1
    ring_color = theme.get("particle_ring", theme["connector_line"])
    draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], outline=ring_color, width=1)
    # 3. Vibrant glow core
    r_mid = max(3, int(r_glow * 0.65))
    draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], fill=theme["particle_glow"])
    # 4. Pure white highlight center
    draw.ellipse([cx - r_core, cy - r_core, cx + r_core, cy + r_core], fill=theme["particle_core"])

def render_animated_frames(base_img, paths, theme_key, duration=16.0, fps=12):
    theme = THEMES[theme_key]
    total_frames = int(duration * fps)
    frames = []

    for f_idx in range(total_frames):
        curr_time = f_idx / fps
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)

        for path in paths:
            pts = path["pts"]
            period = path.get("period", 2.0)

            t = (curr_time / period) % 1.0
            pos = interpolate_path(pts, t)

            t_tail = ((curr_time - 0.08) / period) % 1.0
            pos_tail = interpolate_path(pts, t_tail)

            draw.ellipse([pos_tail[0]-2.5, pos_tail[1]-2.5, pos_tail[0]+2.5, pos_tail[1]+2.5], fill=theme["particle_glow"])
            draw_popping_particle(draw, pos, theme, r_glow=7, r_core=3)

        frames.append(frame.convert("RGB"))

    return frames

# ==============================================================================
# 7. HIGH-FIDELITY GIF EXPORTER (256 COLORS, DITHER=NONE)
# ==============================================================================
def find_ffmpeg():
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except ImportError:
        pass

    try:
        res = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    return None

def export_pure_gif(frames, output_gif, fps=12):
    ffmpeg_exe = find_ffmpeg()

    if ffmpeg_exe:
        temp_dir = Path("/tmp/linkedin_gif_frames")
        temp_dir.mkdir(parents=True, exist_ok=True)

        for i, f in enumerate(frames):
            f.save(temp_dir / f"frame_{i:04d}.png")

        palette_file = temp_dir / "palette.png"

        cmd_pal = [
            ffmpeg_exe, "-y",
            "-framerate", str(fps),
            "-i", str(temp_dir / "frame_%04d.png"),
            "-vf", "palettegen=stats_mode=full:max_colors=256:reserve_transparent=0",
            str(palette_file)
        ]
        subprocess.run(cmd_pal, capture_output=True, check=True)

        cmd_gif = [
            ffmpeg_exe, "-y",
            "-framerate", str(fps),
            "-i", str(temp_dir / "frame_%04d.png"),
            "-i", str(palette_file),
            "-lavfi", "paletteuse=dither=none:diff_mode=rectangle",
            "-loop", "0",
            output_gif
        ]
        subprocess.run(cmd_gif, capture_output=True, check=True)

        for f in temp_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass
    else:
        duration_ms = int(1000 / fps)
        frames[0].save(
            output_gif,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True
        )

# ==============================================================================
# 8. DEFAULT CONTENT (NO TAKEAWAY)
# ==============================================================================
DEFAULT_CONTENT = {
    "title": "Advanced RAG & Retrieval Architectures: GraphRAG vs Dense Vector Search",
    "subtitle": "A Layered Breakdown of How Graphs, Vectors, and Hybrid Retrieval Work Together",
    "layers": [
        {
            "name": "Ingestion & Indexing",
            "desc": "Parsing, chunking & embeddings",
            "badge": "1",
            "substrate": "Dense Vectors & Tokens",
            "items": [
                "Document Parsing & Cleaning (Clean Raw Text)",
                "Semantic Chunking (Context Boundaries)",
                "Metadata Extraction (Schema & Dates)",
                "Dense Embedding Generation (768/1536d)",
                "Vector Indexing (HNSW & IVF)"
            ]
        },
        {
            "name": "Graph Construction",
            "desc": "Entity networks & communities",
            "badge": "2",
            "substrate": "Knowledge Graph Substrate",
            "items": [
                "Entity Extraction & Resolution (Named Entities)",
                "Relationship Extraction (Predicates & Edges)",
                "Knowledge Graph Creation (Graph DB Substrate)",
                "Community Detection & Clusters (Leiden / Louvain)",
                "Community Summarization (Hierarchical Themes)"
            ]
        },
        {
            "name": "Core Retrieval Engine",
            "desc": "Hybrid search & multi-hop (HERO)",
            "badge": "3",
            "hero": True,
            "substrate": "Fused Hybrid Context",
            "items": [
                "Dense Vector Search (Semantic K-NN)",
                "Sparse Keyword Search (BM25 Precision)",
                "Graph Traversal & Multi-Hop (Entity Expansion)",
                "Hybrid Search & Reranking (Cross-Encoder / RRF)",
                "Global Community Search (Broad Synthesis)"
            ]
        },
        {
            "name": "Reasoning & Synthesis",
            "desc": "Fusion, grounding & generation",
            "badge": "4",
            "substrate": "Grounded Synthesis",
            "items": [
                "Context Fusion & Ranking (Re-ordered Context)",
                "Context Window Management (Token Budgeting)",
                "LLM-Based Answer Generation (Synthesized Reply)",
                "Source Citations & Grounding (Attributed Facts)",
                "Faithfulness Validation (Hallucination Guard)"
            ]
        },
        {
            "name": "Production & Monitoring",
            "desc": "Metrics, evaluation & feedback",
            "badge": "5",
            "substrate": "Continuous SLA & Evaluation",
            "items": [
                "Retrieval Accuracy & Recall (Hit Rate & MRR)",
                "Latency & Cost Benchmarking (p95, p99, SLA)",
                "Answer Quality Evaluation (Ragas & TruLens)",
                "Graph Freshness & Re-indexing (Incremental Sync)",
                "Feedback Loops & Observability (Traces & Drift)"
            ]
        }
    ],
    "comparison": {
        "left": {
            "title": "Dense Vector Search",
            "pipeline": ["Query", "Dense Embed", "ANN Index", "Top-K Chunks"],
            "bullets": [
                "Semantic similarity matching across dense embedding space",
                "Strong for focused, factoid and local passage questions",
                "Fast, horizontally scalable retrieval (sub-50ms latency)",
                "Limited explicit relationship and multi-hop traversal"
            ]
        },
        "right": {
            "title": "GraphRAG (Knowledge Graph Augmented)",
            "pipeline": ["Query", "Entity Extr", "Graph Walk", "Communities", "Fused Context"],
            "bullets": [
                "Entity and relationship-aware multi-hop graph retrieval",
                "Deep reasoning across interconnected, non-contiguous facts",
                "Precomputed community summaries for global / thematic questions",
                "Higher construction complexity; combined with dense vectors for hybrid"
            ]
        }
    }
}

# ==============================================================================
# 9. CLI ENTRYPOINT
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate LinkedIn animated architecture GIFs matching authentic reference post styling."
    )
    parser.add_argument(
        "-c", "--content",
        help="Path to JSON or prompt text file containing post title, layers, items, flow, and comparison, OR raw text/JSON string."
    )
    parser.add_argument(
        "-t", "--theme",
        choices=["royal_amethyst", "champagne_bronze", "graphite_blue", "4", "5", "6", "amethyst", "bronze", "blue"],
        default="champagne_bronze",
        help="Theme selection (User's choice of 3: royal_amethyst [#4], champagne_bronze [#5], graphite_blue [#6])."
    )
    parser.add_argument(
        "-s", "--size",
        default="auto",
        help="Canvas size preset (auto | 1200x630 | 1080x1350 | 1080x1080 | 1400x800 | custom WIDTHxHEIGHT)."
    )
    parser.add_argument(
        "-f", "--font",
        choices=["modern", "times"],
        default="modern",
        help="Font family selection: modern (display sans-serif as in reference posts) or times (Times New Roman)."
    )
    parser.add_argument(
        "-o", "--output",
        default="linkedin_architecture.gif",
        help="Output GIF path (default: linkedin_architecture.gif). ONLY the GIF is created."
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Frame rate in FPS (default: 12)."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=16.0,
        help="Loop duration in seconds (default: 16.0)."
    )
    return parser.parse_args()

def main():
    args = parse_args()

    theme_key = THEME_ALIASES.get(args.theme.lower(), "champagne_bronze")
    theme_name = THEMES[theme_key]["name"]
    print(f"Applying Theme: [{THEMES[theme_key]['id']}] {theme_name}")

    if args.content:
        content = parse_content_input(args.content)
        if not content.get("title") and not content.get("layers"):
            print("Warning: Parsed content had no title or layers, falling back to default.", file=sys.stderr)
            content = DEFAULT_CONTENT
    else:
        print("Using default Advanced RAG & Retrieval Architecture content specification.")
        content = DEFAULT_CONTENT

    width, height = resolve_canvas_size(args.size, content)
    print(f"Canvas Dimensions: {width} x {height} (Preset/Mode: {args.size})")

    print(f"Building authentic reference layout (Theme: {theme_name}, Font: {args.font}, No Takeaway)...")
    base_img, paths = render_base_diagram(width, height, content, theme_key, font_family=args.font)

    print(f"Rendering simultaneous flow across all {len(paths)} paths ({args.duration}s @ {args.fps} FPS)...")
    frames = render_animated_frames(base_img, paths, theme_key, duration=args.duration, fps=args.fps)

    output_path = args.output
    if not output_path.lower().endswith(".gif"):
        output_path += ".gif"

    print(f"Exporting pure razor-sharp animated GIF (256 colors, dither=none) to: {output_path} ...")
    export_pure_gif(frames, output_path, fps=args.fps)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Success! Generated pure LinkedIn GIF: {output_path} ({file_size_mb:.2f} MB)")
    print("Only the GIF has been created as requested.")

# ==============================================================================
# 10. PRODUCTION PROGRAMMATIC ENGINE
# ==============================================================================
class LinkedInGifEngine:
    """Production service for generating and customizing animated LinkedIn architectural GIFs."""

    @staticmethod
    def design_architecture_spec(topic: str, post_draft: str) -> str:
        """Use LLM to analyze the post and generate an exhaustive, deeply informative 5-layer architecture spec.

        Strictly follows INPUT_GUIDE.md format:
        - Two-tone Title with colon: <Prefix Text>: <Key Topic Words>
        - Subtitle
        - 5 Layers with 4-5 bullet points each in `<Item Title> (<Detail 1, Detail 2>)` format
        - Layer 3 as Hero stage
        - Bottom Comparison: <Concept A> vs <Concept B> with 4 detailed bullets each
        - Rich depth of real technical detail directly expanding upon the post content
        - Zero asterisks, zero markdown code fences, NO takeaway banner
        """
        from lib.llm_client import llm_client

        system_prompt = """
You are an Elite Systems Architect and Technical Diagram Author for Tier-1 Tech Publications.
Given a LinkedIn post draft, design an exhaustive, highly informative, production-grade 5-layer architecture specification that grounds and visually maps out the post's core technical concepts.

CRITICAL REQUIREMENTS (Strictly adhere to the LinkedIn GIF Engine Input Guide):
1. Give immense technical depth: Every bullet point must have concrete engineering mechanics, protocols, memory/latency trade-offs, or real infrastructure components (e.g. HNSW, Cross-Encoder, p95/p99 SLAs, KV Cache, PagedAttention, vLLM, TensorRT-LLM, RoPE, FP8, LoRA, FlashAttention-3).
2. Format: Output strictly plain text matching this EXACT syntax (do NOT wrap in markdown code fences):

Title: <Prefix Text>: <Key Topic Words>
Subtitle: <Comprehensive one-line subtitle describing the end-to-end architecture>

Layer 1 — <Stage Name> (<Short Subtitle>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)

Layer 2 — <Stage Name> (<Short Subtitle>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)

Layer 3 — <Hero Stage Name> (<Short Subtitle>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)

Layer 4 — <Stage Name> (<Short Subtitle>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)

Layer 5 — <Stage Name> (<Short Subtitle>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)
- <Item Title> (<Detail 1, Detail 2>)

Bottom Comparison: <Concept A> vs <Concept B>

<Concept A>
- <Bullet Point 1>
- <Bullet Point 2>
- <Bullet Point 3>
- <Bullet Point 4>

<Concept B>
- <Bullet Point 1>
- <Bullet Point 2>
- <Bullet Point 3>
- <Bullet Point 4>

CONSTRAINTS:
- The Title MUST have a colon (':') separating the dark prefix from the colored accent words.
- Each layer MUST have 4 to 5 bullet points in `<Title> (<Details>)` format.
- Do NOT output any "Takeaway" line.
- Do NOT use markdown bolding (no asterisks).
"""
        prompt = f"Topic: {topic}\n\nPost Draft:\n{post_draft}\n\nGenerate the complete, deep architecture specification text now:"
        try:
            raw = llm_client.generate(prompt, system_prompt=system_prompt, temperature=0.3).strip()
            # Clean markdown code blocks if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw = "\n".join(lines).strip()
            return raw
        except Exception as e:
            logger.error(f"Failed to generate architecture spec via LLM: {e}")
            return """Title: Advanced Systems: Architecture & Dataflow
Subtitle: End-to-end production pipeline and operational boundaries

Layer 1 — Ingestion & Protocol (Client & Gateway)
- Request Dispatcher (HTTP/2, gRPC streaming)
- Token Authentication (JWT, rate limiter)
- Schema Validator (Pydantic, OpenAPI)
- Load Balancing (Round-robin, latency-based)

Layer 2 — Embedding & Memory (Dense Index)
- Dense Embedding (768d/1536d vectors)
- HNSW Indexing (Hierarchical graph, M=16)
- Metadata Filtering (Scalar pre-filtering)
- IVF Partitioning (Inverted file clusters)

Layer 3 — Core Orchestration Engine (Multi-Agent Routing)
- Task Decomposition (Sub-goal planning)
- Parallel Dispatch (Async coroutines)
- Tool Invocation (API executor, sandboxed)
- State Synchronization (Shared memory bus)

Layer 4 — Synthesis & Grounding (Model Layer)
- Context Assembly (Budgeted token window)
- LLM Inference (vLLM, continuous batching)
- Output Verification (Hallucination check)
- Citation Injection (Attributed source spans)

Layer 5 — Observability & Telemetry (SLA Guardrails)
- Latency Profiler (TTFT, ITL benchmarks)
- Quality Evaluation (Faithfulness metrics)
- Trace Collector (OpenTelemetry spans)
- Alerting & Feedback (Drift detection)

Bottom Comparison: Monolithic Agent vs Multi-Agent Orchestration

Monolithic Agent
- Single context window handling planning and tool calls
- Prone to context saturation and prompt drift
- Simple deployment topology with zero network hop latency
- Difficult to benchmark individual cognitive steps

Multi-Agent Orchestration
- Decoupled specialized roles with isolated sub-prompts
- Parallel execution across independent task branches
- Resilient recovery with isolated failure boundaries
- Requires distributed state bus and telemetry tracing
"""

    @staticmethod
    def render_gif(content_input, theme: str = "5", size: str = "poster", output_path: Optional[str] = None, fps: int = 10, duration: float = 4.0) -> str:
        """Render animated LinkedIn GIF and return output file path."""
        theme_key = THEME_ALIASES.get(str(theme).lower(), "champagne_bronze")
        if isinstance(content_input, (dict, list)):
            content = content_input
        else:
            content = parse_content_input(str(content_input))

        if not content.get("title") and not content.get("layers"):
            content = DEFAULT_CONTENT

        width, height = resolve_canvas_size(size, content)
        base_img, paths = render_base_diagram(width, height, content, theme_key, font_family="modern")
        frames = render_animated_frames(base_img, paths, theme_key, duration=duration, fps=fps)

        if not output_path:
            out_dir = Path("data/generated_gifs")
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"arch_{int(time.time())}.gif")

        if not output_path.lower().endswith(".gif"):
            output_path += ".gif"

        export_pure_gif(frames, output_path, fps=fps)
        return output_path

gif_engine = LinkedInGifEngine()

if __name__ == "__main__":
    main()

