import os
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from core.config import config

logger = logging.getLogger(__name__)

class ImageClient:
    """Renders professional high-DPI architecture diagrams and animated GIFs for LinkedIn posts."""

    def __init__(self):
        self.output_dir = config.DATA_DIR / "generated_cards"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.font_badge = self._get_font(bold=True, size=18)
        self.font_title = self._get_font(bold=True, size=40)
        self.font_sub = self._get_font(bold=False, size=20)
        self.font_layer_title = self._get_font(bold=True, size=21)
        self.font_pill = self._get_font(bold=True, size=17)
        self.font_footer = self._get_font(bold=False, size=18)

    def _get_font(self, bold: bool = False, size: int = 18):
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
        for p in font_paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def render_architecture_frame(self, data: dict, highlighted_layer: int = -1, width: int = 1200, height: int = 1350) -> Image.Image:
        """Renders an architectural layer-by-layer frame."""
        img = Image.new("RGBA", (width, height), (13, 17, 23, 255)) # Dark GitHub/AWS midnight background
        
        # 1. Subtle Radial Glow Background
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.ellipse([(100, -100), (1100, 400)], fill=(30, 41, 59, 140))
        g_draw.ellipse([(200, 800), (1000, 1400)], fill=(30, 27, 75, 120))
        glow = glow.filter(ImageFilter.GaussianBlur(80))
        img.paste(glow, (0, 0), glow)

        draw = ImageDraw.Draw(img)

        # 2. Geometric Tech Grid Lines
        for x in range(60, width, 100):
            draw.line([(x, 60), (x, height - 60)], fill=(255, 255, 255, 8), width=1)
        for y in range(60, height, 100):
            draw.line([(60, y), (width - 60, y)], fill=(255, 255, 255, 8), width=1)

        # Top Tag / Category Badge
        badge_text = "GEN AI ARCHITECTURE ECOSYSTEM // DEEP DIVE"
        draw.rounded_rectangle([(70, 45), (550, 85)], radius=12, fill=(30, 41, 59, 230), outline=(56, 189, 248, 220), width=2)
        draw.text((90, 54), badge_text, fill=(56, 189, 248), font=self.font_badge)

        # Main Title & Subtitle
        title = data.get("system_title", "Production Gen AI Stack Simplified")
        draw.text((70, 102), title.upper(), fill=(255, 255, 255), font=self.font_title)
        
        subtitle = data.get("system_subtitle", "Breaking down the end-to-end architecture into practical layers")
        draw.text((70, 155), subtitle, fill=(148, 163, 184), font=self.font_sub)

        # Horizontal Divider Line
        draw.line([(70, 195), (width - 70, 195)], fill=(51, 65, 85), width=2)

        # 3. Render Layers
        layers = data.get("layers", [])
        num_layers = max(1, len(layers))
        start_y = 215
        available_height = height - start_y - 120
        layer_spacing = 16
        layer_h = int((available_height - (num_layers - 1) * layer_spacing) / num_layers)

        colors = [
            {"border": (56, 189, 248), "fill": (15, 23, 42), "tag": (56, 189, 248)},    # Cyan
            {"border": (129, 140, 248), "fill": (15, 23, 42), "tag": (129, 140, 248)}, # Indigo
            {"border": (52, 211, 153), "fill": (15, 23, 42), "tag": (52, 211, 153)},   # Emerald
            {"border": (251, 191, 36), "fill": (15, 23, 42), "tag": (251, 191, 36)},   # Amber
            {"border": (244, 114, 182), "fill": (15, 23, 42), "tag": (244, 114, 182)}, # Pink
            {"border": (167, 139, 250), "fill": (15, 23, 42), "tag": (167, 139, 250)}, # Purple
        ]

        for i, layer in enumerate(layers):
            y1 = start_y + i * (layer_h + layer_spacing)
            y2 = y1 + layer_h
            
            c = colors[i % len(colors)]
            is_active = (highlighted_layer == -1) or (highlighted_layer == i)

            if is_active:
                border_color = c["border"]
                bg_color = (20, 29, 47, 240) if highlighted_layer == i else (15, 23, 42, 230)
                tag_color = c["tag"]
                border_w = 3 if highlighted_layer == i else 2
                pill_bg = (30, 41, 59, 240)
                pill_text = (241, 245, 249)
                pill_border = c["border"]
            else:
                border_color = (51, 65, 85, 120)
                bg_color = (15, 23, 42, 120)
                tag_color = (100, 116, 139)
                border_w = 1
                pill_bg = (20, 28, 42, 140)
                pill_text = (148, 163, 184)
                pill_border = (51, 65, 85)

            # Draw Layer Card
            draw.rounded_rectangle([(70, y1), (width - 70, y2)], radius=16, fill=bg_color, outline=border_color, width=border_w)

            # Layer Title
            layer_num = layer.get("layer_number", i + 1)
            layer_name = layer.get("name", f"LAYER {layer_num}")
            draw.text((95, y1 + 18), f"LAYER {layer_num}: {layer_name}", fill=tag_color, font=self.font_layer_title)

            # Tool Pills
            tools = layer.get("tools", [])
            px = 95
            py = y1 + 58
            pill_h = 38
            
            for tool in tools:
                bbox = draw.textbbox((0, 0), tool, font=self.font_pill)
                tw = bbox[2] - bbox[0]
                pill_w = tw + 28

                if px + pill_w > width - 90:
                    break

                draw.rounded_rectangle([(px, py), (px + pill_w, py + pill_h)], radius=10, fill=pill_bg, outline=pill_border, width=1)
                draw.text((px + 14, py + 8), tool, fill=pill_text, font=self.font_pill)
                px += pill_w + 12

            # Downward connection indicator
            if i < num_layers - 1:
                arrow_y = y2 + 2
                arrow_color = c["border"] if is_active else (71, 85, 105)
                draw.text(((width // 2) - 8, arrow_y), "v", fill=arrow_color, font=self.font_badge)

        # 4. Footer Takeaway Card
        footer_y = height - 90
        draw.rounded_rectangle([(70, footer_y), (width - 70, height - 35)], radius=14, fill=(15, 23, 42, 230), outline=(56, 189, 248, 160), width=2)
        takeaway = data.get("takeaway", "The real skill is understanding which service belongs at each stage and how they connect.")
        draw.text((95, footer_y + 16), f"KEY TAKEAWAY: {takeaway}", fill=(226, 232, 240), font=self.font_footer)

        return img.convert("RGB")

    def generate_architecture_diagram(self, data: dict, return_gif: bool = True) -> str:
        """Generate high-DPI architecture diagram (PNG + Animated GIF) and return chosen file path."""
        prefix = f"arch_{os.getpid()}_{abs(hash(data.get('system_title', 'stack'))) % 10000}"
        png_path = self.output_dir / f"{prefix}.png"
        gif_path = self.output_dir / f"{prefix}.gif"

        # 1. Render and save PNG
        static_img = self.render_architecture_frame(data, highlighted_layer=-1)
        static_img.save(png_path, "PNG", quality=95)
        logger.info(f"Generated static architecture PNG: {png_path}")

        if not return_gif:
            return str(png_path)

        # 2. Render and save Animated GIF
        layers = data.get("layers", [])
        num_layers = len(layers)
        frames = []
        for i in range(num_layers):
            frames.append(self.render_architecture_frame(data, highlighted_layer=i))
        
        all_active = self.render_architecture_frame(data, highlighted_layer=-1)
        frames.append(all_active)
        frames.append(all_active)

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=[650] * num_layers + [1800, 1800],
            loop=0,
            optimize=True
        )
        logger.info(f"Generated animated architecture GIF: {gif_path}")
        return str(gif_path)

image_client = ImageClient()
