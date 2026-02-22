#!/usr/bin/env python3
"""
Generate CJK bitmap font headers for InkHUD from a TTF font.

Usage:
    python3 generate_cjk_font.py <ttf_path> <cell_size> <output.h> [options]

Options:
    --var-prefix PREFIX    Variable name prefix (default: CJKFont<cell_size>px)
    --render-size SIZE     TTF render size in pixels (default: cell_size * 2)
    --y-offset OFFSET      yOffset value for glyph positioning (default: -cell_size)
    --x-advance ADVANCE    xAdvance value for cursor movement (default: cell_size + 1)
    --max-kanji N          Maximum number of kanji to include (default: all)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# Codepoint aliases: map new codepoint to existing one
# e.g., new Joyo 𠮟 (U+20B9F) -> old form 叱 (U+53F1)
CODEPOINT_ALIASES = {
    0x20B9F: 0x53F1,  # 𠮟 -> 叱 (shikaru - new Joyo form to old form)
}


# Punctuation positioning categories
# Bottom: 、。…‥＿ (comma, period, ellipsis, underscore)
BOTTOM_PUNCT = {0x3001, 0x3002, 0x2026, 0x2025, 0xFF3F, 0xFF0C, 0xFF0E}
# Opening brackets (align to right): 「『（【〔〈《
OPEN_BRACKETS = {0x300C, 0x300E, 0xFF08, 0x3010, 0x3014, 0x3008, 0x300A}
# Closing brackets (align to left/bottom): 」』）】〕〉》
CLOSE_BRACKETS = {0x300D, 0x300F, 0xFF09, 0x3011, 0x3015, 0x3009, 0x300B}
# Top: quotes
TOP_PUNCT = {0xFF40, 0x201C, 0x2018, 0x201D, 0x2019, 0xFF02, 0xFF07, 0x301D, 0x301E}
# Center: ー〜・＊；：＝ and most others
CENTER_PUNCT = {0x30FC, 0x301C, 0x30FB, 0xFF0A, 0xFF1B, 0xFF1A, 0xFF1D, 0xFF0B, 0xFF0D, 0xFF5C}


def get_punct_mode(codepoint):
    """Determine positioning mode for punctuation."""
    if codepoint in BOTTOM_PUNCT:
        return 'bottom'
    elif codepoint in OPEN_BRACKETS:
        return 'open'
    elif codepoint in CLOSE_BRACKETS:
        return 'close'
    elif codepoint in TOP_PUNCT:
        return 'top'
    elif codepoint in CENTER_PUNCT:
        return 'center'
    elif 0x3000 <= codepoint <= 0x303F:
        return 'center'  # Default for other CJK punctuation
    return None


def get_japanese_codepoints(max_kanji=None):
    """Get all Japanese codepoints to include in the font."""
    codepoints = set()

    # Hiragana: U+3041-U+3096
    for cp in range(0x3041, 0x3097):
        codepoints.add(cp)

    # Katakana: U+30A1-U+30FA + prolonged sound mark
    for cp in range(0x30A1, 0x30FB):
        codepoints.add(cp)
    codepoints.add(0x30FC)

    codepoints.add(0x3000)  # Ideographic space

    for ch in "。、・「」『』（）【】〜〇々〈〉《》〒〝〞〟":
        codepoints.add(ord(ch))

    for ch in "？！，．：；＠＃＄％＆＊＋－＝＜＞／＼｜＿～＾｀":
        codepoints.add(ord(ch))

    for ch in "（）［］｛｝「」『』【】＂＇":
        codepoints.add(ord(ch))

    for cp in range(0xFF10, 0xFF1A):
        codepoints.add(cp)
    for cp in range(0xFF21, 0xFF3B):
        codepoints.add(cp)
    for cp in range(0xFF41, 0xFF5B):
        codepoints.add(cp)

    for ch in "→←↑↓○●◎△▲▽▼□■◇◆★☆※†‡":
        codepoints.add(ord(ch))

    for ch in "¢£¥￠￡￥²³×÷¼½¾℃♠♣♥♦♪":
        codepoints.add(ord(ch))

    # Ellipsis (for proper bottom positioning)
    codepoints.add(0x2026)  # …
    codepoints.add(0x2025)  # ‥

    for cp in range(0xFF65, 0xFFA0):
        codepoints.add(cp)

    # Kanji (limited if max_kanji specified)
    kanji_list = get_joyo_kanji()
    if max_kanji is not None and max_kanji < len(kanji_list):
        kanji_list = kanji_list[:max_kanji]
    for ch in kanji_list:
        codepoints.add(ord(ch))

    # Add old form of 叱 (U+53F1) for alias support (𠮟 -> 叱)
    codepoints.add(0x53F1)

    return sorted(codepoints)


def get_joyo_kanji():
    """Load all 2136 Joyo kanji from joyo_kanji.txt file."""
    script_dir = Path(__file__).parent
    kanji_file = script_dir / "joyo_kanji.txt"

    if not kanji_file.exists():
        print(f"Warning: {kanji_file} not found")
        return []

    kanji = []
    with open(kanji_file, 'r', encoding='utf-8') as f:
        for line in f:
            ch = line.strip()
            if ch and len(ch) == 1:
                kanji.append(ch)

    return kanji


def render_glyph(font, codepoint, cell_size, render_size):
    """Render a single glyph to a fixed-size bitmap cell with proper punctuation positioning."""
    char = chr(codepoint)

    try:
        bbox = font.getbbox(char)
        if bbox is None or (bbox[2] - bbox[0]) == 0:
            return None
    except Exception:
        return None

    # Get font metrics
    ascent, descent = font.getmetrics()
    punct_mode = get_punct_mode(codepoint)

    # Create canvas
    canvas_size = render_size * 2
    img = Image.new('L', (canvas_size, canvas_size), 0)
    draw = ImageDraw.Draw(img)

    # Draw position depends on punctuation mode
    draw_x = render_size // 2
    if punct_mode == 'bottom':
        draw_y = render_size  # Lower position for bottom punctuation
    else:
        draw_y = render_size // 2
    draw.text((draw_x, draw_y), char, font=font, fill=255, anchor='mm')

    # Find actual bbox
    pixels = img.load()
    min_x, min_y, max_x, max_y = canvas_size, canvas_size, 0, 0
    for y in range(canvas_size):
        for x in range(canvas_size):
            if pixels[x, y] > 0:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < min_x:
        return None

    glyph_w = max_x - min_x + 1
    glyph_h = max_y - min_y + 1

    # Fixed crop size for consistent scaling
    crop_size = ascent + 4

    if punct_mode == 'bottom':
        # Position glyph at bottom of cell
        cx = (min_x + max_x) // 2
        crop_left = cx - crop_size // 2
        crop_top = max_y - crop_size  # Align to bottom edge
    elif punct_mode == 'top':
        # Position glyph at top of cell
        cx = (min_x + max_x) // 2
        crop_left = cx - crop_size // 2
        crop_top = min_y - 2
    elif punct_mode == 'open':
        # Opening bracket: align to right side of cell
        crop_left = max_x - crop_size + 6
        crop_top = min_y - 4
    elif punct_mode == 'close':
        # Closing bracket: align to left side of cell
        crop_left = min_x - 6
        crop_top = max_y - crop_size + 4
    elif punct_mode == 'center':
        # Center the glyph
        cx = (min_x + max_x) // 2
        cy = (min_y + max_y) // 2
        crop_left = cx - crop_size // 2
        crop_top = cy - crop_size // 2
    else:
        # Kanji/Kana: tight crop centered on glyph
        crop_size = max(glyph_w, glyph_h) + 4
        cx = (min_x + max_x) // 2
        cy = (min_y + max_y) // 2
        crop_left = cx - crop_size // 2
        crop_top = cy - crop_size // 2

    # Ensure bounds
    crop_left = max(0, crop_left)
    crop_top = max(0, crop_top)
    crop_right = min(canvas_size, crop_left + crop_size)
    crop_bottom = min(canvas_size, crop_top + crop_size)

    crop = img.crop((crop_left, crop_top, crop_right, crop_bottom))

    # Scale to cell_size
    result = crop.resize((cell_size, cell_size), Image.LANCZOS)

    # Threshold
    result = result.point(lambda p: 1 if p > 64 else 0, '1')

    # Pack to bytes
    bitmap = []
    byte_val = 0
    bit = 7
    result_pixels = result.load()
    for y in range(cell_size):
        for x in range(cell_size):
            if result_pixels[x, y]:
                byte_val |= (1 << bit)
            bit -= 1
            if bit < 0:
                bitmap.append(byte_val)
                byte_val = 0
                bit = 7

    if bit < 7:
        bitmap.append(byte_val)

    return bytes(bitmap)


def make_blank_glyph(cell_size):
    """Create an empty bitmap for invisible glyphs like fullwidth space."""
    total_bits = cell_size * cell_size
    total_bytes = (total_bits + 7) // 8
    return bytes(total_bytes)


def generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance, max_kanji):
    """Generate a C header file with CJK bitmap font data."""
    print(f"Loading font: {ttf_path}")
    font = ImageFont.truetype(str(ttf_path), render_size)

    codepoints = get_japanese_codepoints(max_kanji)
    kanji_count = len([cp for cp in codepoints if 0x4E00 <= cp <= 0x9FFF])
    print(f"Processing {len(codepoints)} codepoints ({kanji_count} kanji, cell={cell_size}px)...")

    force_blank = {0x3000}
    glyphs = []
    skipped = 0

    for cp in codepoints:
        if cp in force_blank:
            glyphs.append((cp, make_blank_glyph(cell_size)))
            continue

        result = render_glyph(font, cp, cell_size, render_size)
        if result is not None:
            glyphs.append((cp, result))
        else:
            skipped += 1

    print(f"  Rendered: {len(glyphs)} glyphs, skipped: {skipped}")

    glyphs.sort(key=lambda g: g[0])

    bitmap_data = bytearray()
    glyph_entries = []
    for cp, bmp in glyphs:
        offset = len(bitmap_data)
        bitmap_data.extend(bmp)
        glyph_entries.append((cp, offset))

    total_kb = (len(bitmap_data) + len(glyph_entries) * 6) / 1024
    print(f"  Bitmap: {len(bitmap_data) / 1024:.1f} KB, table: {len(glyph_entries) * 6 / 1024:.1f} KB, total: {total_kb:.1f} KB")

    with open(output_path, 'w') as f:
        f.write(f"// Auto-generated CJK bitmap font: {cell_size}px cell, {render_size}px render\n")
        f.write(f"// Source: {Path(ttf_path).name}\n")
        f.write(f"// Glyphs: {len(glyphs)} ({kanji_count} kanji), Bitmap: {len(bitmap_data)} bytes\n")
        f.write(f"// Features: Punctuation positioning, codepoint aliases\n\n")
        f.write("#pragma once\n\n")
        f.write("#include \"graphics/niche/Fonts/CJK/CJKFont.h\"\n\n")

        f.write(f"const uint8_t {var_prefix}Bitmaps[] PROGMEM = {{\n")
        for i in range(0, len(bitmap_data), 16):
            chunk = bitmap_data[i:i + 16]
            f.write("    " + ", ".join(f"0x{b:02X}" for b in chunk) + ",\n")
        f.write("};\n\n")

        f.write(f"const NicheGraphics::CJKGlyph {var_prefix}Glyphs[] PROGMEM = {{\n")
        for cp, offset in glyph_entries:
            ch = chr(cp)
            f.write(f"    {{ 0x{cp:04X}, {offset:6d} }}, // {ch}\n")
        f.write("};\n\n")

        f.write(f"const NicheGraphics::CJKFont {var_prefix} PROGMEM = {{\n")
        f.write(f"    {var_prefix}Bitmaps,\n")
        f.write(f"    {var_prefix}Glyphs,\n")
        f.write(f"    {len(glyphs)},  // glyphCount\n")
        f.write(f"    {cell_size},    // width\n")
        f.write(f"    {cell_size},    // height\n")
        f.write(f"    {x_advance},    // xAdvance\n")
        f.write(f"    {y_offset},     // yOffset\n")
        f.write("};\n\n")

        # Write codepoint aliases
        if CODEPOINT_ALIASES:
            f.write("// Codepoint aliases: map unsupported codepoints to existing glyphs\n")
            f.write("// Used for characters like 𠮟 (U+20B9F) which should display as 叱 (U+53F1)\n")
            f.write("struct CJKAlias {\n")
            f.write("    uint32_t from;  // Requested codepoint\n")
            f.write("    uint32_t to;    // Codepoint to use instead\n")
            f.write("};\n\n")
            f.write(f"const CJKAlias {var_prefix}Aliases[] PROGMEM = {{\n")
            for from_cp, to_cp in CODEPOINT_ALIASES.items():
                from_char = chr(from_cp) if from_cp < 0x10000 else f"U+{from_cp:05X}"
                to_char = chr(to_cp)
                f.write(f"    {{ 0x{from_cp:05X}, 0x{to_cp:04X} }},  // {from_char} -> {to_char}\n")
            f.write("};\n")
            f.write(f"const uint16_t {var_prefix}AliasCount = {len(CODEPOINT_ALIASES)};\n")

    print(f"  Written: {output_path}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    ttf_path = sys.argv[1]
    cell_size = int(sys.argv[2])
    output_path = sys.argv[3]

    var_prefix = f"CJKFont{cell_size}px"
    render_size = int(cell_size * 2)  # Increased for better quality
    y_offset = -cell_size
    x_advance = cell_size + 1
    max_kanji = None

    args = sys.argv[4:]
    i = 0
    while i < len(args):
        if args[i] == "--var-prefix" and i + 1 < len(args):
            var_prefix = args[i + 1]
            i += 2
        elif args[i] == "--render-size" and i + 1 < len(args):
            render_size = int(args[i + 1])
            i += 2
        elif args[i] == "--y-offset" and i + 1 < len(args):
            y_offset = int(args[i + 1])
            i += 2
        elif args[i] == "--x-advance" and i + 1 < len(args):
            x_advance = int(args[i + 1])
            i += 2
        elif args[i] == "--max-kanji" and i + 1 < len(args):
            max_kanji = int(args[i + 1])
            i += 2
        else:
            print(f"Unknown option: {args[i]}")
            i += 1

    generate_font_header(ttf_path, cell_size, render_size, output_path, var_prefix, y_offset, x_advance, max_kanji)


if __name__ == "__main__":
    main()
