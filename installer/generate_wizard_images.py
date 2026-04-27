"""
Generate Inno Setup wizard images for EduraSync installer.

Outputs (in the same directory as this script):
  wizard_sidebar.bmp   164 x 314  — Welcome / Finish page left panel
  wizard_header.bmp     55 x  55  — Inner-page top-right icon
  app_icon.ico          multi-size — Setup executable icon

Run from the repo root:
  python installer/generate_wizard_images.py
"""

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Pillow not installed – running: pip install pillow")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT   = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT    = Path(__file__).resolve().parent   # installer/

# ── Brand colours (match app theme) ─────────────────────────────────────────
DARK_TOP  = ( 10,  25,  47)   # #0A1929  deep navy
DARK_BOT  = ( 15,  52,  96)   # #0F3460  mid navy
ACCENT    = ( 34, 139, 230)   # #228BE6
WHITE     = (255, 255, 255)
FOOTER_BG = (  6,  14,  30)   # almost black


# ── Font helpers ─────────────────────────────────────────────────────────────

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    win_bold   = ["C:/Windows/Fonts/segoeuib.ttf",  "C:/Windows/Fonts/calibrib.ttf"]
    win_normal = ["C:/Windows/Fonts/segoeui.ttf",   "C:/Windows/Fonts/calibri.ttf"]
    linux_bold   = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"]
    linux_normal = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/dejavu/DejaVuSans.ttf"]
    candidates = (win_bold + linux_bold) if bold else (win_normal + linux_normal)
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


def _center_text(draw: ImageDraw.Draw, text: str, y: int, width: int,
                  font, fill=WHITE) -> None:
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text(((width - tw) // 2, y), text, font=font, fill=fill)


# ── Background gradient ───────────────────────────────────────────────────────

def _gradient(img: Image.Image, top: tuple, bot: tuple) -> None:
    draw = ImageDraw.Draw(img)
    for y in range(img.height):
        t = y / (img.height - 1)
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (img.width, y)], fill=(r, g, b, 255))


# ── Remove near-black background from logo ────────────────────────────────────

def _strip_black_bg(src: Image.Image, threshold: int = 40) -> Image.Image:
    """
    Convert near-black pixels to transparent so the logo can be placed on
    any background.  Works well for the EDURA logo (black bg, coloured text).
    """
    import numpy as np
    img = src.convert("RGBA")
    arr = np.array(img)
    # Mask pixels where R, G and B are all below threshold
    mask = (arr[:, :, 0] < threshold) & (arr[:, :, 1] < threshold) & (arr[:, :, 2] < threshold)
    arr[mask, 3] = 0
    return Image.fromarray(arr, "RGBA")


# ── Sidebar  164 × 314 ────────────────────────────────────────────────────────

def make_sidebar(icon_path: Path, logo_path: Path, out_path: Path) -> None:
    W, H = 164, 314
    img = Image.new("RGBA", (W, H))
    _gradient(img, DARK_TOP, DARK_BOT)

    draw = ImageDraw.Draw(img)

    # ── subtle dot-grid texture ──────────────────────────────────────────────
    for x in range(10, W, 20):
        for y in range(10, H, 20):
            draw.ellipse([x, y, x + 1, y + 1], fill=(255, 255, 255, 18))

    # ── thin top accent bar ──────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 3], fill=(*ACCENT, 200))

    # ── app icon (transparent bg, works perfectly on dark) ───────────────────
    ICON_SIZE = 68
    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

    # soft glow ring behind icon
    glow_r = ICON_SIZE // 2 + 10
    cx = W // 2
    top_pad = 20
    glow_bb = [cx - glow_r, top_pad, cx + glow_r, top_pad + glow_r * 2]
    draw.ellipse(glow_bb, fill=(*ACCENT, 30))

    ix = cx - ICON_SIZE // 2
    iy = top_pad + 6
    img.paste(icon, (ix, iy), icon)

    # ── logo wordmark (black bg stripped → transparent) ───────────────────────
    logo_src = Image.open(logo_path).convert("RGBA")
    logo_no_bg = _strip_black_bg(logo_src, threshold=30)

    # Crop to tight bounding box (remove empty transparent margins)
    bb = logo_no_bg.getbbox()
    if bb:
        logo_no_bg = logo_no_bg.crop(bb)

    # Scale to fit in 144 px width while keeping aspect ratio
    logo_target_w = 144
    lw, lh = logo_no_bg.size
    logo_target_h = int(lh * logo_target_w / lw)
    logo_scaled = logo_no_bg.resize((logo_target_w, logo_target_h), Image.LANCZOS)

    lx = (W - logo_target_w) // 2
    ly = iy + ICON_SIZE + 10
    img.paste(logo_scaled, (lx, ly), logo_scaled)

    # ── "Sync System" sub-label ──────────────────────────────────────────────
    y_sub = ly + logo_target_h + 4
    font_sub = _load_font(8)
    _center_text(draw, "Attendance Sync System", y_sub, W, font_sub,
                  (180, 210, 255, 220))

    # ── separator ────────────────────────────────────────────────────────────
    sep_y = y_sub + 18
    draw.rectangle([16, sep_y, W - 16, sep_y + 1], fill=(255, 255, 255, 40))

    # ── feature bullets ───────────────────────────────────────────────────────
    bullets = [
        "ZKTeco device sync",
        "Cloud attendance upload",
        "Offline-first storage",
        "Auto background sync",
    ]
    font_b = _load_font(8)
    by = sep_y + 12
    for line in bullets:
        draw.ellipse([16, by + 3, 19, by + 6], fill=(*ACCENT, 200))
        draw.text((25, by), line, font=font_b, fill=(200, 225, 255, 210))
        by += 17

    # ── footer band ──────────────────────────────────────────────────────────
    foot_h = 36
    foot_y = H - foot_h
    draw.rectangle([0, foot_y, W, H], fill=(*FOOTER_BG, 240))
    draw.rectangle([0, foot_y, W, foot_y + 1], fill=(*ACCENT, 80))

    font_pub = _load_font(8, bold=True)
    font_url = _load_font(7)
    _center_text(draw, "Softzenix IT",     foot_y + 6,  W, font_pub, WHITE)
    _center_text(draw, "softzenixbd.com",  foot_y + 20, W, font_url,
                  (140, 190, 255, 200))

    img.convert("RGB").save(str(out_path))
    print(f"  Wrote {out_path}  ({W}×{H})")


# ── Header  55 × 55 ──────────────────────────────────────────────────────────

def make_header(icon_path: Path, out_path: Path) -> None:
    W = H = 55
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # White base with a faint accent border circle
    draw.ellipse([1, 1, W - 2, H - 2],
                  fill=(231, 245, 255, 255),
                  outline=(*ACCENT, 160), width=2)

    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((36, 36), Image.LANCZOS)
    img.paste(icon, ((W - 36) // 2, (H - 36) // 2), icon)

    img.convert("RGB").save(str(out_path))
    print(f"  Wrote {out_path}  ({W}×{H})")


def make_setup_icon(icon_path: Path, out_path: Path) -> None:
    # Inno Setup requires a valid .ico for SetupIconFile.
    # Generate a multi-resolution ICO from the source PNG.
    icon = Image.open(icon_path).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(str(out_path), format="ICO", sizes=sizes)
    print(f"  Wrote {out_path}  (ICO sizes: {', '.join(f'{w}x{h}' for w, h in sizes)})")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    icon = ASSETS / "icon.png"
    logo = ASSETS / "logo.png"

    for p in (icon, logo):
        if not p.exists():
            print(f"ERROR: asset not found at {p}")
            sys.exit(1)

    print("Generating Inno Setup wizard images…")
    make_sidebar(icon, logo, OUT / "wizard_sidebar.bmp")
    make_header(icon,        OUT / "wizard_header.bmp")
    make_setup_icon(icon,    OUT / "app_icon.ico")
    print("Done.")


if __name__ == "__main__":
    main()
